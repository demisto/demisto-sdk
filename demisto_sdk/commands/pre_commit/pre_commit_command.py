import itertools
import logging
import multiprocessing
import os
import re
import shutil
import subprocess
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import more_itertools
from packaging.version import Version

from demisto_sdk.commands.common.constants import INTEGRATIONS_DIR, SCRIPTS_DIR
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.pycln import PyclnHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.hooks.run_unit_tests import RunUnitTestHook

logger = logging.getLogger("demisto-sdk")
yaml = YAML_Handler()
json = JSON_Handler()

GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS")
DEFAULT_PYTHON_VERSION = "3.10"
DEFAULT_PYTHON2_VERSION = "2.7"

PRECOMMIT_TEMPLATE_PATH = Path(__file__).parent / ".pre-commit-config_template.yaml"
PRECOMMIT_PATH = CONTENT_PATH / ".pre-commit-config.yaml"

SKIPPED_HOOKS = {"format", "validate"}

INTEGRATION_SCRIPT_REGEX = re.compile(r"^Packs/.*/(?:Integrations|Scripts)/.*.yml$")


with open(PRECOMMIT_TEMPLATE_PATH) as f:
    PRECOMMIT_TEMPLATE = yaml.load(f)


@dataclass
class PreCommitRunner:
    """This class is responsible of running pre-commit hooks."""

    python_version_to_files: Dict[str, Set[Path]]

    def __post_init__(self):
        """
        We initialize the hooks and all files for later use.
        """
        self.all_files = set(itertools.chain.from_iterable(self.python_version_to_files.values()))
        
    def hooks(self, pre_commit_config: dict) -> dict:
        hooks = {}
        for repo in pre_commit_config["repos"]:
            for hook in repo["hooks"]:
                hooks[hook["id"]] = hook
        return hooks

    def prepare_hooks(
        self,
        pre_commit_config: dict,
        python_version: str,
        fix: bool,
        native_images: bool,
    ) -> None:
        hooks = self.hooks(pre_commit_config)
        PyclnHook(hooks["pycln"]).prepare_hook(PYTHONPATH)
        RuffHook(hooks["ruff"]).prepare_hook(python_version, fix, GITHUB_ACTIONS)
        MypyHook(hooks["mypy"]).prepare_hook(python_version)
        RunUnitTestHook(hooks["run-unit-tests"]).prepare_hook(native_images)

    def run(
        self,
        test: bool = False,
        skip_hooks: Optional[List[str]] = None,
        validate: bool = False,
        format: bool = False,
        native_images: bool = False,
        verbose: bool = False,
        show_diff_on_failure: bool = False,
        fix: bool = False,
    ) -> int:
        # handle skipped hooks
        ret_val = 0
        precommit_env = os.environ.copy()
        skipped_hooks: set = SKIPPED_HOOKS
        skipped_hooks |= set(skip_hooks or [])
        if os.getenv("CI"):
            # No reason to update the docker-image on CI?
            skipped_hooks.add("update-docker-image")
        if not test and not native_images:
            skipped_hooks.add("run-unit-tests")
        if validate:
            skipped_hooks.remove("validate")
        if format:
            skipped_hooks.remove("format")

        precommit_env["SKIP"] = ",".join(skipped_hooks)
        precommit_env["PYTHONPATH"] = ":".join(str(path) for path in PYTHONPATH)
        precommit_env["MYPYPATH"] = ":".join(str(path) for path in PYTHONPATH)

        for python_version, changed_files in self.python_version_to_files.items():
            precommit_config = deepcopy(PRECOMMIT_TEMPLATE)
            logger.info(
                f"Running pre-commit for {changed_files} with python version {python_version}"
            )
            if python_version.startswith("2"):
                with open(PRECOMMIT_PATH, "w") as f:
                    yaml.dump(precommit_config, f)
                if test:
                    response = subprocess.run(
                        [
                            "pre-commit",
                            "run",
                            "run-unit-tests",
                            "--files",
                            *changed_files,
                            "-v" if verbose else "",
                        ],
                        env=precommit_env,
                        cwd=CONTENT_PATH,
                    )
                    if response.returncode:
                        ret_val = response.returncode
                continue
            self.prepare_hooks(precommit_config, python_version, fix, native_images)
            with open(PRECOMMIT_PATH, "w") as f:
                yaml.dump(precommit_config, f)
            # use chunks because OS does not support such large comments
            for chunk in more_itertools.chunked_even(changed_files, 10_000):
                response = subprocess.run(
                    [
                        "pre-commit",
                        "run",
                        "--files",
                        *chunk,
                        "-v" if verbose else "",
                        "--show-diff-on-failure" if show_diff_on_failure else "",
                    ],
                    env=precommit_env,
                    cwd=CONTENT_PATH,
                )
                if response.returncode:
                    ret_val = 1
        # remove the config file in the end of the file
        shutil.rmtree(PRECOMMIT_PATH, ignore_errors=True)
        return ret_val


def categorize_files(files: Set[Path]) -> PreCommitRunner:
    """This function categorizes the files to run pre-commit on, and returns the PreCommitRunner object.

    Args:
        files (Set[Path]): files to run pre-commit on.

    Raises:
        Exception: If invalid files were given.

    Returns:
        PreCommitRunner: PreCommitRunner object.
    """
    integrations_scripts_mapping = defaultdict(set)
    files_to_run = []
    for file in files:
        if file.is_dir():
            continue
        if set(file.parts) & {INTEGRATIONS_DIR, SCRIPTS_DIR}:
            find_path_index = (
                i + 1
                for i, part in enumerate(file.parts)
                if part in {INTEGRATIONS_DIR, SCRIPTS_DIR}
            )
            if not find_path_index:
                raise Exception(f"Could not find integration/script path for {file}")
            integration_script_path = Path(*file.parts[: next(find_path_index) + 1])
            integrations_scripts_mapping[integration_script_path].add(file)
        else:
            files_to_run.append(file)

    python_versions_to_files = defaultdict(set)
    with multiprocessing.Pool() as pool:
        integrations_scripts = pool.map(
            BaseContent.from_path, integrations_scripts_mapping.keys()
        )

    for integration_script in integrations_scripts:
        if not integration_script or not isinstance(
            integration_script, IntegrationScript
        ):
            continue
        integration_script_path = integration_script.path.parent
        if python_version_string := integration_script.python_version:
            version = Version(python_version_string)
            python_version_string = f"{version.major}.{version.minor}"
        python_versions_to_files[python_version_string or DEFAULT_PYTHON2_VERSION].update(
            integrations_scripts_mapping[integration_script_path]
            | {integration_script.path}
        )

    python_versions_to_files[DEFAULT_PYTHON_VERSION].update(files_to_run)

    return PreCommitRunner(python_versions_to_files)


def pre_commit_manager(
    input_files: Optional[Iterable[Path]] = None,
    use_git: bool = False,
    staged_only: bool = False,
    all_files: bool = False,
    test: bool = False,
    skip_hooks: Optional[List[str]] = None,
    validate: bool = False,
    format: bool = False,
    native_images: bool = False,
    verbose: bool = False,
    show_diff_on_failure: bool = False,
    fix: bool = False,
) -> int:
    """Run pre-commit hooks .

    Args:
        input_files (Iterable[Path], optional): Input files to run pre-commit on. Defaults to None.
        use_git (bool, optional): Whether use git to determine precommit files. Defaults to False.
        staged_only (bool, optional): Whether to run only on staged filed. Defaults to False.
        all_files (bool, optional): Whether to run on all_files. Defaults to False.
        test (bool, optional): Whether to run unit-tests. Defaults to False.
        skip_hooks (Optional[List[str]], optional): List of hooks to skip. Defaults to None.
        force_run_hooks (Optional[List[str]], optional): List for hooks to force run. Defaults to None.
        verbose (bool, optional): Whether run pre-commit in verbose mode. Defaults to False.
        show_diff_on_failure (bool, optional): Whether show git diff after pre-commit failure. Defaults to False.
        fix (bool, optional): Whether fixing code file. Defaults to False.

    Returns:
        int: Return code of pre-commit.
    """
    # We have imports to this module, however it does not exists in the repo.
    (CONTENT_PATH / "CommonServerUserPython.py").touch()

    if not any((input_files, staged_only, use_git, all_files)):
        logger.debug("No arguments were given, running on git changed files")
        use_git = True

    files_to_run = preprocess_files(input_files, use_git, staged_only, all_files)
    pre_commit_runner = categorize_files(files_to_run)
    return pre_commit_runner.run(
        test,
        skip_hooks,
        validate,
        format,
        native_images,
        verbose,
        show_diff_on_failure,
        fix,
    )


def preprocess_files(
    input_files: Optional[Iterable[Path]],
    use_git: bool = False,
    staged_only: bool = False,
    all_files: bool = False,
) -> Set[Path]:
    git_util = GitUtil()
    staged_files = git_util._get_staged_files()
    if input_files:
        raw_files = set(input_files)
    elif staged_only:
        raw_files = staged_files
    elif use_git:
        raw_files = staged_files | git_util._get_all_changed_files()
    elif all_files:
        raw_files = git_util.get_all_files()
    else:
        raw_files = set()

    files_to_run: Set[Path] = set()
    for file in raw_files:
        if file.is_dir():
            files_to_run |= set(file.rglob("*"))
        else:
            files_to_run.add(file)

    # Convert to absolute paths
    files_to_run = {file.absolute() for file in files_to_run}
    return files_to_run
