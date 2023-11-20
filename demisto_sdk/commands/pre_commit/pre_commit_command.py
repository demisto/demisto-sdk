import itertools
import multiprocessing
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEFAULT_PYTHON2_VERSION,
    DEFAULT_PYTHON_VERSION,
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_file_or_remote,
    get_last_remote_release_version,
    get_remote_file,
    string_to_bool,
    write_dict,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.pre_commit.hooks.docker import DockerHook
from demisto_sdk.commands.pre_commit.hooks.hook import Hook, join_files
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.pycln import PyclnHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.hooks.sourcery import SourceryHook
from demisto_sdk.commands.pre_commit.hooks.validate_format import ValidateFormatHook

IS_GITHUB_ACTIONS = string_to_bool(os.getenv("GITHUB_ACTIONS"), False)

PRECOMMIT_TEMPLATE_NAME = ".pre-commit-config_template.yaml"
PRECOMMIT_TEMPLATE_PATH = CONTENT_PATH / PRECOMMIT_TEMPLATE_NAME
PRECOMMIT_PATH = CONTENT_PATH / ".pre-commit-config-content.yaml"
SOURCERY_CONFIG_PATH = CONTENT_PATH / ".sourcery.yaml"

SKIPPED_HOOKS = {"format", "validate", "secrets"}

INTEGRATION_SCRIPT_REGEX = re.compile(r"^Packs/.*/(?:Integrations|Scripts)/.*.yml$")

PYTHON2_SUPPORTED_HOOKS = {
    "check-json",
    "check-yaml",
    "check-ast",
    "check-merge-conflict",
    "run-unit-tests",
    "validate",
    "format",
}


@dataclass
class PreCommitRunner:
    """This class is responsible of running pre-commit hooks."""

    input_mode: bool
    all_files: bool
    mode: str
    python_version_to_files: Dict[str, Set[Path]]
    demisto_sdk_commit_hash: str

    def __post_init__(self):
        """
        We initialize the hooks and all_files for later use.
        """
        self.files_to_run = set(
            itertools.chain.from_iterable(self.python_version_to_files.values())
        )
        self.precommit_template = get_file_or_remote(PRECOMMIT_TEMPLATE_PATH)
        remote_config_file = get_remote_file(str(PRECOMMIT_TEMPLATE_PATH))
        if remote_config_file and remote_config_file != self.precommit_template:
            logger.info(
                f"Your local {PRECOMMIT_TEMPLATE_NAME} is not up to date to the remote one."
            )
        if not isinstance(self.precommit_template, dict):
            raise TypeError(
                f"Pre-commit template in {PRECOMMIT_TEMPLATE_PATH} is not a dictionary."
            )
        if self.mode:
            logger.info(
                f"[yellow]Running pre-commit hooks in `{self.mode}` mode.[/yellow]"
            )
        # changes the demisto-sdk revision to the latest release version (or the debug commit hash)
        # to debug, modify the DEMISTO_SDK_COMMIT_HASH_DEBUG variable to your demisto-sdk commit hash
        self._get_repos(self.precommit_template)[
            "https://github.com/demisto/demisto-sdk"
        ]["rev"] = self.demisto_sdk_commit_hash
        self.hooks = self._get_hooks(self.precommit_template)

    @staticmethod
    def _get_repos(pre_commit_config: dict) -> dict:
        repos = {}
        for repo in pre_commit_config["repos"]:
            repos[repo["repo"]] = repo
        return repos

    def _get_hooks(self, pre_commit_config: dict) -> dict:
        hooks = {}
        for repo in pre_commit_config["repos"]:
            for hook in repo["hooks"]:
                hooks[hook["id"]] = {
                    "repo": repo,
                    "hook": hook,
                }
                # if the hook has a skip key, we add it to the SKIPPED_HOOKS set
                if hook.pop("skip", None):
                    SKIPPED_HOOKS.add(hook["id"])
        return hooks

    def exclude_python2_of_non_supported_hooks(self) -> None:
        """
        This function handles the python2 files.
        Files with python2 run only the hooks that in PYTHON2_SUPPORTED_HOOKS.
        """
        python2_files = self.python_version_to_files.get(DEFAULT_PYTHON2_VERSION)
        if not python2_files:
            return

        logger.info(
            f"Python {DEFAULT_PYTHON2_VERSION} files running only with the following hooks: {', '.join(PYTHON2_SUPPORTED_HOOKS)}"
        )

        join_files_string = join_files(python2_files)
        for hook in self.hooks.values():
            if hook["hook"]["id"] in PYTHON2_SUPPORTED_HOOKS:
                continue
            elif hook["hook"].get("exclude"):
                hook["hook"]["exclude"] += f"|{join_files_string}"
            else:
                hook["hook"]["exclude"] = join_files_string

    def prepare_hooks(
        self,
        hooks: dict,
        run_docker_hooks,
    ) -> None:
        kwargs = {
            "mode": self.mode,
            "all_files": self.all_files,
            "input_mode": self.input_mode,
        }
        if "pycln" in hooks:
            PyclnHook(**hooks.pop("pycln"), **kwargs).prepare_hook(PYTHONPATH)
        if "ruff" in hooks:
            RuffHook(**hooks.pop("ruff"), **kwargs).prepare_hook(
                self.python_version_to_files, IS_GITHUB_ACTIONS
            )
        if "mypy" in hooks:
            MypyHook(**hooks.pop("mypy"), **kwargs).prepare_hook(
                self.python_version_to_files
            )
        if "sourcery" in hooks:
            SourceryHook(**hooks.pop("sourcery"), **kwargs).prepare_hook(
                self.python_version_to_files, config_file_path=SOURCERY_CONFIG_PATH
            )
        if "validate" in hooks:
            ValidateFormatHook(**hooks.pop("validate"), **kwargs).prepare_hook(
                self.files_to_run
            )
        if "format" in hooks:
            ValidateFormatHook(**hooks.pop("format"), **kwargs).prepare_hook(
                self.files_to_run
            )
        [
            DockerHook(**hook, **kwargs).prepare_hook(
                files_to_run=self.files_to_run, run_docker_hooks=run_docker_hooks
            )
            for hook_id, hook in hooks.items()
            if hook_id.endswith("in-docker")
        ]
        hooks_without_docker = [
            hook for hook_id, hook in hooks.items() if not hook_id.endswith("in-docker")
        ]
        for hook in hooks_without_docker:
            Hook(**hook, **kwargs).prepare_hook()

    def run(
        self,
        unit_test: bool = False,
        skip_hooks: Optional[List[str]] = None,
        validate: bool = False,
        format: bool = False,
        secrets: bool = False,
        verbose: bool = False,
        show_diff_on_failure: bool = False,
        exclude_files: Optional[Set[Path]] = None,
        dry_run: bool = False,
        run_docker_hooks: bool = True,
    ) -> int:
        ret_val = 0
        precommit_env = os.environ.copy()
        skipped_hooks: set = SKIPPED_HOOKS
        skipped_hooks.update(set(skip_hooks or ()))
        if not unit_test:
            skipped_hooks.add("run-unit-tests")
            skipped_hooks.add("coverage-analyze")
            skipped_hooks.add("merge-coverage-report")
        if validate and "validate" in skipped_hooks:
            skipped_hooks.remove("validate")
        if format and "format" in skipped_hooks:
            skipped_hooks.remove("format")
        if secrets and "secrets" in skipped_hooks:
            skipped_hooks.remove("secrets")
        precommit_env["SKIP"] = ",".join(sorted(skipped_hooks))
        precommit_env["PYTHONPATH"] = ":".join(str(path) for path in sorted(PYTHONPATH))
        # The PYTHONPATH should be the same as the PYTHONPATH, but without the site-packages because MYPY does not support it
        precommit_env["MYPYPATH"] = ":".join(
            str(path) for path in sorted(PYTHONPATH) if "site-packages" not in str(path)
        )
        precommit_env["DEMISTO_SDK_CONTENT_PATH"] = str(CONTENT_PATH)

        self.exclude_python2_of_non_supported_hooks()

        for (
            python_version,
            changed_files_by_version,
        ) in self.python_version_to_files.items():
            changed_files_string = ", ".join(
                sorted(str(file) for file in changed_files_by_version)
            )
            logger.info(
                f"Running pre-commit with Python {python_version} on {changed_files_string}"
            )

        self.prepare_hooks(self.hooks, run_docker_hooks)
        if self.all_files:
            self.precommit_template["exclude"] += f"|{join_files(exclude_files or {})}"
        else:
            self.precommit_template["files"] = join_files(self.files_to_run)

        write_dict(PRECOMMIT_PATH, data=self.precommit_template)

        if dry_run:
            logger.info(
                "Dry run, skipping pre-commit.\nConfig file saved to .pre-commit-config-content.yaml"
            )
            return ret_val
        response = subprocess.run(
            list(
                filter(
                    None,
                    [
                        sys.executable,
                        "-m",
                        "pre_commit",
                        "run",
                        "-a",
                        "-c",
                        str(PRECOMMIT_PATH),
                        "--show-diff-on-failure" if show_diff_on_failure else "",
                        "-v" if verbose else "",
                    ],
                )
            ),
            env=precommit_env,
            cwd=CONTENT_PATH,
        )
        if response.returncode:
            ret_val = 1

        # remove the config file in the end of the flow
        PRECOMMIT_PATH.unlink(missing_ok=True)
        return ret_val


def group_by_python_version(files: Set[Path]) -> Tuple[Dict[str, Set], Set[Path]]:
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
            code_file_path = CONTENT_PATH / Path(
                *file.parts[: next(find_path_index) + 1]
            )
            integrations_scripts_mapping[code_file_path].add(file)
        else:
            infra_files.append(file)

    python_versions_to_files: Dict[str, Set] = defaultdict(set)
    with multiprocessing.Pool() as pool:
        integrations_scripts = pool.map(
            BaseContent.from_path, integrations_scripts_mapping.keys()
        )

    exclude_integration_script = set()
    for integration_script in integrations_scripts:
        if not integration_script or not isinstance(
            integration_script, IntegrationScript
        ):
            continue
        if integration_script.deprecated:
            if integration_script.is_unified:
                exclude_integration_script.add(
                    integration_script.path.relative_to(CONTENT_PATH)
                )
            else:
                exclude_integration_script.add(
                    integration_script.path.parent.relative_to(CONTENT_PATH)
                )
            continue

        code_file_path = integration_script.path.parent
        if python_version := integration_script.python_version:
            version = Version(python_version)
            python_version_string = f"{version.major}.{version.minor}"
        else:
            # Skip cases of powershell scripts
            exclude_integration_script.add(
                integration_script.path.relative_to(CONTENT_PATH)
            )
            continue
        python_versions_to_files[
            python_version_string or DEFAULT_PYTHON2_VERSION
        ].update(
            integrations_scripts_mapping[code_file_path],
            {integration_script.path.relative_to(CONTENT_PATH)},
        )

    if infra_files:
        python_versions_to_files[DEFAULT_PYTHON_VERSION].update(infra_files)

    if exclude_integration_script:
        logger.info(
            f"Skipping deprecated or powershell integrations or scripts: {join_files(exclude_integration_script, ', ')}"
        )
    return python_versions_to_files, exclude_integration_script


def pre_commit_manager(
    input_files: Optional[Iterable[Path]] = None,
    staged_only: bool = False,
    commited_only: bool = False,
    git_diff: bool = False,
    all_files: bool = False,
    mode: str = "",
    unit_test: bool = False,
    skip_hooks: Optional[List[str]] = None,
    validate: bool = False,
    format: bool = False,
    secrets: bool = False,
    verbose: bool = False,
    show_diff_on_failure: bool = False,
    sdk_ref: Optional[str] = None,
    dry_run: bool = False,
    run_docker_hooks: bool = True,
) -> Optional[int]:
    """Run pre-commit hooks .

    Args:
        input_files (Iterable[Path], optional): Input files to run pre-commit on. Defaults to None.
        staged_only (bool, optional): Whether to run on staged files only. Defaults to False.
        commited_only (bool, optional): Whether to run on commited files only. Defaults to False.
        git_diff (bool, optional): Whether use git to determine precommit files. Defaults to False.
        all_files (bool, optional): Whether to run on all_files. Defaults to False.
        mode (str): The mode to run pre-commit in. Defaults to empty str.
        test (bool, optional): Whether to run unit-tests. Defaults to False.
        skip_hooks (Optional[List[str]], optional): List of hooks to skip. Defaults to None.
        force_run_hooks (Optional[List[str]], optional): List for hooks to force run. Defaults to None.
        verbose (bool, optional): Whether run pre-commit in verbose mode. Defaults to False.
        show_diff_on_failure (bool, optional): Whether show git diff after pre-commit failure. Defaults to False.
        dry_run (bool, optional): Whether to run the pre-commit hooks in dry-run mode, which will only create the config file.
        run_docker_hooks (bool, optional): Whether to run docker based hooks or not.

    Returns:
        int: Return code of pre-commit.
    """
    # We have imports to this module, however it does not exists in the repo.
    (CONTENT_PATH / "CommonServerUserPython.py").touch()

    if not any((input_files, staged_only, git_diff, all_files)):
        logger.info("No arguments were given, running on staged files and git changes.")
        git_diff = True

    files_to_run = preprocess_files(
        input_files, staged_only, commited_only, git_diff, all_files
    )
    if not files_to_run:
        logger.info("No files were changed, skipping pre-commit.")
        return None

    files_to_run_string = ", ".join(
        sorted((str(changed_path) for changed_path in files_to_run))
    )

    # This is the files that pre-commit received, but in fact it will run on files returned from group_by_python_version
    logger.info(f"pre-commit received the following files: {files_to_run_string}")

    if not sdk_ref:
        sdk_ref = f"v{get_last_remote_release_version()}"
    python_version_to_files, exclude_files = group_by_python_version(files_to_run)
    if not python_version_to_files:
        logger.info("No files to run pre-commit on, skipping pre-commit.")
        return None

    pre_commit_runner = PreCommitRunner(
        bool(input_files), all_files, mode, python_version_to_files, sdk_ref
    )
    return pre_commit_runner.run(
        unit_test,
        skip_hooks,
        validate,
        format,
        secrets,
        verbose,
        show_diff_on_failure,
        exclude_files,
        dry_run,
        run_docker_hooks,
    )


def preprocess_files(
    input_files: Optional[Iterable[Path]] = None,
    staged_only: bool = False,
    commited_only: bool = False,
    use_git: bool = False,
    all_files: bool = False,
) -> Set[Path]:
    git_util = GitUtil()
    staged_files = git_util._get_staged_files()
    all_git_files = git_util.get_all_files().union(staged_files)
    if input_files:
        raw_files = set(input_files)
    elif staged_only:
        raw_files = staged_files
    elif use_git:
        raw_files = git_util._get_all_changed_files()
        if not commited_only:
            raw_files = raw_files.union(staged_files)
    elif all_files:
        raw_files = all_git_files
    else:
        raise ValueError(
            "No files were given to run pre-commit on, and no flags were given."
        )
    files_to_run: Set[Path] = set()
    for file in raw_files:
        if file.is_dir():
            files_to_run.update({path for path in file.rglob("*") if path.is_file()})
        else:
            files_to_run.add(file)
            # If the current file is a yml file, add the matching python file to files_to_run
            if file.suffix == ".yml":
                py_file_path = file.with_suffix(".py")
                if py_file_path.exists():
                    files_to_run.add(py_file_path)

    # convert to relative file to content path
    relative_paths = {
        file.relative_to(CONTENT_PATH) if file.is_absolute() else file
        for file in files_to_run
    }
    # filter out files that are not in the content git repo (e.g in .gitignore)
    return relative_paths & all_git_files
