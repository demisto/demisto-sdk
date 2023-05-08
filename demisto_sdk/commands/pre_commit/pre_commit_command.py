import itertools
import multiprocessing
import os
import re
import subprocess
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import more_itertools

from demisto_sdk.commands.common.constants import (
    DEFAULT_PYTHON2_VERSION,
    DEFAULT_PYTHON_VERSION,
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.docker_helper import get_python_version_from_image
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_last_remote_release_version
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.pycln import PyclnHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook

yaml = YAML_Handler()
json = JSON_Handler()

IS_GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS", False)

PRECOMMIT_TEMPLATE_PATH = Path(__file__).parent / ".pre-commit-config_template.yaml"
PRECOMMIT_PATH = CONTENT_PATH / ".pre-commit-config-content.yaml"

SKIPPED_HOOKS = {"format", "validate"}

INTEGRATION_SCRIPT_REGEX = re.compile(r"^Packs/.*/(?:Integrations|Scripts)/.*.yml$")


@dataclass
class PreCommitRunner:
    """This class is responsible of running pre-commit hooks."""

    python_version_to_files: Dict[str, Set[Path]]
    demisto_sdk_commit_hash: str

    def __post_init__(self):
        """
        We initialize the hooks and all_files for later use.
        """
        self.all_files = set(
            itertools.chain.from_iterable(self.python_version_to_files.values())
        )
        with open(PRECOMMIT_TEMPLATE_PATH) as f:
            self.precommit_template = yaml.load(f)

        # changes the demisto-sdk revision to the latest release version (or the debug commit hash)
        # to debug, modify the DEMISTO_SDK_COMMIT_HASH_DEBUG variable to your demisto-sdk commit hash
        self._get_repos(self.precommit_template)[
            "https://github.com/demisto/demisto-sdk"
        ]["rev"] = self.demisto_sdk_commit_hash

    @staticmethod
    def _get_repos(pre_commit_config: dict) -> dict:
        repos = {}
        for repo in pre_commit_config["repos"]:
            repos[repo["repo"]] = repo
        return repos

    @staticmethod
    def _get_hooks(pre_commit_config: dict) -> dict:
        hooks = {}
        for repo in pre_commit_config["repos"]:
            for hook in repo["hooks"]:
                hooks[hook["id"]] = hook
        return hooks

    def prepare_hooks(
        self,
        pre_commit_config: dict,
        python_version: str,
    ) -> None:
        hooks = self._get_hooks(pre_commit_config)
        PyclnHook(hooks["pycln"]).prepare_hook(PYTHONPATH)
        RuffHook(hooks["ruff"]).prepare_hook(python_version, IS_GITHUB_ACTIONS)
        MypyHook(hooks["mypy"]).prepare_hook(python_version)

    def run(
        self,
        unit_test: bool = False,
        skip_hooks: Optional[List[str]] = None,
        validate: bool = False,
        format: bool = False,
        verbose: bool = False,
        show_diff_on_failure: bool = False,
    ) -> int:
        ret_val = 0
        precommit_env = os.environ.copy()
        skipped_hooks: set = SKIPPED_HOOKS
        skipped_hooks |= set(skip_hooks or [])
        if os.getenv("CI"):
            # No reason to update the docker-image on CI, as we don't commit from the CI
            skipped_hooks.add("update-docker-image")
        if not unit_test:
            skipped_hooks.add("run-unit-tests")
        if validate and "validate" in skipped_hooks:
            skipped_hooks.remove("validate")
        if format and "format" in skipped_hooks:
            skipped_hooks.remove("format")

        precommit_env["SKIP"] = ",".join(sorted(skipped_hooks))
        precommit_env["PYTHONPATH"] = ":".join(str(path) for path in sorted(PYTHONPATH))
        # The PYTHONPATH should be the same as the PYTHONPATH, but without the site-packages because MYPY does not support it
        precommit_env["MYPYPATH"] = ":".join(
            str(path) for path in sorted(PYTHONPATH) if "site-packages" not in str(path)
        )
        for python_version, changed_files in self.python_version_to_files.items():
            precommit_config = deepcopy(self.precommit_template)
            logger.info(
                f"Running pre-commit for {changed_files} with python version {python_version}"
            )
            if python_version.startswith("2"):
                with open(PRECOMMIT_PATH, "w") as f:
                    yaml.dump(precommit_config, f)
                if unit_test:
                    response = subprocess.run(
                        [
                            "pre-commit",
                            "run",
                            "run-unit-tests",
                            "-c",
                            str(PRECOMMIT_PATH),
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
            self.prepare_hooks(precommit_config, python_version)
            with open(PRECOMMIT_PATH, "w") as f:
                yaml.dump(precommit_config, f)
            # use chunks because OS does not support such large comments
            for chunk in more_itertools.chunked_even(changed_files, 10_000):
                response = subprocess.run(
                    [
                        "pre-commit",
                        "run",
                        "-c",
                        str(PRECOMMIT_PATH),
                        "--show-diff-on-failure" if show_diff_on_failure else "",
                        "--files",
                        *chunk,
                        "-v" if verbose else "",
                    ],
                    env=precommit_env,
                    cwd=CONTENT_PATH,
                )
                if response.returncode:
                    ret_val = 1

        # remove the config file in the end of the flow
        PRECOMMIT_PATH.unlink(missing_ok=True)
        return ret_val


def group_by_python_version(files: Set[Path]) -> Dict[str, set]:
    """This function groups the files to run pre-commit on by the python version.

    Args:
        files (Set[Path]): files to run pre-commit on.

    Raises:
        Exception: If invalid files were given.

    Returns:
        Dict[str, set]: The files grouped by their python version.
    """
    integrations_scripts_mapping = defaultdict(set)
    infra_files = []
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
                raise Exception(f"Could not find Integrations/Scripts path for {file}")
            code_file_path = Path(*file.parts[: next(find_path_index) + 1])
            integrations_scripts_mapping[code_file_path].add(file)
        else:
            infra_files.append(file)

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
        code_file_path = integration_script.path.parent
        if python_version := get_python_version_from_image(
            integration_script.docker_image
        ):
            python_version_string = f"{python_version.major}.{python_version.minor}"
        python_versions_to_files[
            python_version_string or DEFAULT_PYTHON2_VERSION
        ].update(
            integrations_scripts_mapping[code_file_path] | {integration_script.path}
        )

    python_versions_to_files[DEFAULT_PYTHON_VERSION].update(infra_files)
    return python_versions_to_files


def pre_commit_manager(
    input_files: Optional[Iterable[Path]] = None,
    git_diff: bool = False,
    all_files: bool = False,
    unit_test: bool = False,
    skip_hooks: Optional[List[str]] = None,
    validate: bool = False,
    format: bool = False,
    verbose: bool = False,
    show_diff_on_failure: bool = False,
    sdk_ref: Optional[str] = None,
) -> int:
    """Run pre-commit hooks .

    Args:
        input_files (Iterable[Path], optional): Input files to run pre-commit on. Defaults to None.
        git_diff (bool, optional): Whether use git to determine precommit files. Defaults to False.
        all_files (bool, optional): Whether to run on all_files. Defaults to False.
        test (bool, optional): Whether to run unit-tests. Defaults to False.
        skip_hooks (Optional[List[str]], optional): List of hooks to skip. Defaults to None.
        force_run_hooks (Optional[List[str]], optional): List for hooks to force run. Defaults to None.
        verbose (bool, optional): Whether run pre-commit in verbose mode. Defaults to False.
        show_diff_on_failure (bool, optional): Whether show git diff after pre-commit failure. Defaults to False.

    Returns:
        int: Return code of pre-commit.
    """
    # We have imports to this module, however it does not exists in the repo.
    (CONTENT_PATH / "CommonServerUserPython.py").touch()

    if not any((input_files, git_diff, all_files)):
        logger.info("No arguments were given, running on staged files and git changes.")
        git_diff = True

    files_to_run = preprocess_files(input_files, git_diff, all_files)
    if not sdk_ref:
        sdk_ref = f"v{get_last_remote_release_version()}"
    pre_commit_runner = PreCommitRunner(group_by_python_version(files_to_run), sdk_ref)
    return pre_commit_runner.run(
        unit_test,
        skip_hooks,
        validate,
        format,
        verbose,
        show_diff_on_failure,
    )


def preprocess_files(
    input_files: Optional[Iterable[Path]],
    use_git: bool = False,
    all_files: bool = False,
) -> Set[Path]:
    git_util = GitUtil()
    staged_files = git_util._get_staged_files()
    if input_files:
        raw_files = set(input_files)
    elif use_git:
        raw_files = git_util._get_all_changed_files() | staged_files
    elif all_files:
        raw_files = git_util.get_all_files() | staged_files
    else:
        raise ValueError(
            "No files were given to run pre-commit on, and no flags were given."
        )
    files_to_run: Set[Path] = set()
    for file in raw_files:
        if file.is_dir():
            files_to_run |= set(file.rglob("*"))
        else:
            files_to_run.add(file)

    # Convert to absolute paths
    return {
        file if file.is_absolute() else CONTENT_PATH / file for file in files_to_run
    }
