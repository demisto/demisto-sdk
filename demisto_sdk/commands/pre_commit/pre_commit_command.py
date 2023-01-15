import logging
import multiprocessing
import os
import re
import shutil
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import more_itertools
from packaging.version import Version
from pkg_resources import get_distribution

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

logger = logging.getLogger("demisto-sdk")
yaml = YAML_Handler()
json = JSON_Handler()

GITHUB_ACTIONS = os.getenv("GITHUB_ACTIONS")
DEFAULT_PYTHON_VERSION = "3.10"
EMPTY_PYTHON_VERSION = "2.7"

PRECOMMIT_TEMPLATE_PATH = Path(__file__).parent / ".pre-commit-config_template.yaml"

SKIPPED_HOOKS = ("format", "validate")

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
        self.hooks = {}
        for repo in PRECOMMIT_TEMPLATE["repos"]:
            for hook in repo["hooks"]:
                self.hooks[hook["id"]] = hook
        self.all_files: Set[Path] = set()
        for _, files in self.python_version_to_files.items():
            self.all_files |= files

    def run(
        self,
        test: bool = False,
        skip_hooks: Optional[List[str]] = None,
        force_run_hooks: Optional[List[str]] = None,
        verbose: bool = False,
        show_diff_on_failure: bool = False,
        no_fix: bool = False,
    ) -> int:
        # handle skipped hooks
        ret_val = 0
        precommit_env = os.environ.copy()
        skipped_hooks = list(SKIPPED_HOOKS)
        skipped_hooks.extend(skip_hooks or [])
        if not test:
            skipped_hooks.append("run-unit-tests")
        if no_fix:
            skipped_hooks.append("autopep8")
        if force_run_hooks:
            skipped_hooks = [
                hook for hook in skipped_hooks if hook not in force_run_hooks
            ]
        precommit_env["SKIP"] = ",".join(skipped_hooks)
        precommit_env["PYTHONPATH"] = ":".join(str(path) for path in PYTHONPATH)
        precommit_env["MYPYPATH"] = ":".join(str(path) for path in PYTHONPATH)
        PyclnHook(self.hooks["pycn"]).prepare_hook(PYTHONPATH)
        for python_version, changed_files in self.python_version_to_files.items():
            logger.info(
                f"Running pre-commit for {changed_files} with python version {python_version}"
            )
            if python_version.startswith("2"):
                # python2 supports only unit-tests?
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
                    if response.returncode != 0:
                        ret_val = response.returncode
                continue
            RuffHook(self.hooks["ruff"]).prepare_hook(
                python_version, no_fix, GITHUB_ACTIONS
            )
            if python_version != DEFAULT_PYTHON_VERSION:
                MypyHook(self.hooks["mypy"]).prepare_hook(python_version)
            with open(CONTENT_PATH / ".pre-commit-config.yaml", "w") as f:
                yaml.dump(PRECOMMIT_TEMPLATE, f)
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
        shutil.rmtree(CONTENT_PATH / ".pre-commit-config.yaml", ignore_errors=True)
        return ret_val


def pre_commit_manager(
    input_files: Optional[Iterable[Path]] = None,
    use_git: bool = False,
    staged_only: bool = False,
    all_files: bool = False,
    test: bool = False,
    skip_hooks: Optional[List[str]] = None,
    force_run_hooks: Optional[List[str]] = None,
    verbose: bool = False,
    show_diff_on_failure: bool = False,
    no_fix: bool = False,
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
        no_fix (bool, optional): Whether skip fixing code file. Defaults to False.

    Returns:
        int: Return code of pre-commit.
    """
    # We have imports to this module, however it does not exists in the repo.
    (CONTENT_PATH / "CommonServerUserPython.py").touch()

    if not any((input_files, staged_only, use_git, all_files)):
        use_git = True
    git_util = GitUtil()
    staged_files = git_util._get_staged_files()
    files_to_run: Set[Path] = set()
    if input_files:
        # convert all paths to relative paths
        files_to_run = {
            file.relative_to(CONTENT_PATH) if file.is_absolute() else file
            for file in input_files
        }
    elif staged_only:
        files_to_run = staged_files
    elif use_git:
        files_to_run = staged_files | git_util._get_all_changed_files()
    elif all_files:
        files_to_run = git_util.get_all_files()
    return categorize_files(files_to_run).run(
        test, skip_hooks, force_run_hooks, verbose, show_diff_on_failure, no_fix
    )


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
        integration_script_path = integration_script.path.parent.relative_to(
            CONTENT_PATH
        )
        if python_version := integration_script.python_version:
            version = Version(python_version)
            python_version = f"{version.major}.{version.minor}"
        python_versions_to_files[python_version or EMPTY_PYTHON_VERSION].update(
            integrations_scripts_mapping[integration_script_path]
            | {integration_script.path.relative_to(CONTENT_PATH)}
        )
    python_versions_to_files[DEFAULT_PYTHON_VERSION].update(files_to_run)

    return PreCommitRunner(python_versions_to_files)
