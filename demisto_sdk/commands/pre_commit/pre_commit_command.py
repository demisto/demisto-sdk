import functools
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

import more_itertools
from docker.errors import DockerException
from ruamel.yaml.scalarstring import LiteralScalarString
from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEFAULT_PYTHON2_VERSION,
    DEFAULT_PYTHON_VERSION,
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PreCommitModes,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.docker_helper import get_docker, get_python_version
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_file_or_remote,
    get_last_remote_release_version,
    get_remote_file,
    get_yaml,
    string_to_bool,
    write_dict,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.lint.helpers import get_test_modules
from demisto_sdk.commands.pre_commit.hooks.hook import join_files
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.pycln import PyclnHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.hooks.sourcery import SourceryHook
from demisto_sdk.commands.pre_commit.hooks.validate_format import ValidateFormatHook
from demisto_sdk.commands.run_unit_tests.unit_tests_runner import DOCKER_PYTHONPATHv2

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


@functools.cache
def docker_image_for_file(py_file) -> str:
    # is this more expensive? Should use regex?
    if not py_file.name.endswith(".py"):
        return ""

    yml_in_directory = [f for f in os.listdir(py_file.parent) if f.endswith(".yml")]
    if (
        len(yml_in_directory) == 1
        and (yml_file := py_file.parent / yml_in_directory[0]).is_file()
    ):

        yml = get_yaml(yml_file)
        return yml.get("dockerimage") or yml.get("script", {}).get("dockerimage", "")

    else:
        logger.debug(f"Yml file was not found for py file {py_file}")
        return ""


@functools.cache
def devtest_image(param):
    image, errors = get_docker().pull_or_create_test_image(param)
    if errors:
        raise DockerException(errors)
    else:
        return image


def file_exact_match_regex(files_to_run_on_hook: list[str]) -> str:
    """
    Creates a string to override a hooks 'files' property
    Args:
        files_to_run_on_hook: The files to match

    Returns:
        A string representing the regex to put into a precommit file to return exact file matching

    """
    return "(?x)^(\n" + "|\n".join(files_to_run_on_hook) + "\n)$"


@functools.cache
def get_docker_python_path():
    ":".join(str(path) for path in sorted(DOCKER_PYTHONPATHv2))


@dataclass
class PreCommitRunner:
    """This class is responsible of running pre-commit hooks."""

    input_mode: bool
    all_files: bool
    mode: Optional[PreCommitModes]
    python_version_to_files: Dict[str, Set[Path]]
    demisto_sdk_commit_hash: str
    git_util: GitUtil

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
    ) -> None:
        kwargs = {
            "mode": self.mode,
            "all_files": self.all_files,
            "input_mode": self.input_mode,
        }
        PyclnHook(**hooks["pycln"], **kwargs).prepare_hook(PYTHONPATH)
        RuffHook(**hooks["ruff"], **kwargs).prepare_hook(
            self.python_version_to_files, IS_GITHUB_ACTIONS
        )
        MypyHook(**hooks["mypy"], **kwargs).prepare_hook(self.python_version_to_files)
        SourceryHook(**hooks["sourcery"], **kwargs).prepare_hook(
            self.python_version_to_files, config_file_path=SOURCERY_CONFIG_PATH
        )
        ValidateFormatHook(**hooks["validate"], **kwargs).prepare_hook(
            self.files_to_run
        )
        ValidateFormatHook(**hooks["format"], **kwargs).prepare_hook(self.files_to_run)
    def docker_tag_to_python_files(self) -> dict:

        allfiles = set.union(*[x[1] for x in self.python_version_to_files.items()])
        return {
            devtest_image(image): list(group)
            for image, group in itertools.groupby(
                [file for file in allfiles if docker_image_for_file(file)],
                lambda f: docker_image_for_file(f),
            )
        }

    def set_files_on_hook(self, hook, files) -> int:
        """
        Mutates a hook, setting a regex for file exact match on the hook
        according to the file's *file* and *exclude* properties
        Args:
            hook: The hook to mutate
            files: The files to set on the hook
        Returns:
            The number of files set
        """
        if files_reg := hook.get("files"):
            include_pattern = re.compile(files_reg)
        if exclude_reg := hook.get("exclude"):
            exclude_pattern = re.compile(exclude_reg)
        files_to_run_on_hook = [
            file
            for file in [str(file) for file in files]
            if file in self.git_util.get_all_files()
            and not files_reg
            or re.search(include_pattern, file)  # include all if not defined
            and not (exclude_reg and re.search(exclude_pattern, file))
        ]  # only exclude if defined
        hook["files"] = LiteralScalarString(
            file_exact_match_regex(files_to_run_on_hook)
        )
        hook.pop("exclude", None)
        return len(files_to_run_on_hook)

    def prepare_docker_hooks(self, hooks) -> list:
        all_hooks = []
        tag_to_fies: dict[str, list] = self.docker_tag_to_python_files()
        for hook in hooks:
            counter = 0  # added for uniqueness
            for tag, files in tag_to_fies.items():
                counter = counter + 1
                new_hook = hook.copy()
                new_hook["id"] = f"{hook['id']}-{counter}"
                new_hook["language"] = "docker_image"
                new_hook[
                    "entry"
                ] = f"--entrypoint '{hook['entry']}' -e {get_docker_python_path()} {tag}"
                number_files_set = self.set_files_on_hook(new_hook, files)
                if number_files_set:
                    all_hooks.append(new_hook)
        return all_hooks

    def update_config_with_docker_hooks(self, hooks, config):
        docker_hooks = [v for k, v in hooks.items() if k.endswith("in-docker")]
        prepared_docker_hooks = self.prepare_docker_hooks(docker_hooks)
        if local_repo := [r for r in config["repos"] if r["repo"] == "local"]:
            local_repo = local_repo[0]

            for i, hook in reversed(list(enumerate(local_repo["hooks"]))):
                if hook["id"] in [hook.get("id") for hook in docker_hooks]:
                    del local_repo["hooks"][i]

            local_repo["hooks"].extend(prepared_docker_hooks)


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
    ) -> int:
        ret_val = 0
        precommit_env = os.environ.copy()
        skipped_hooks: set = SKIPPED_HOOKS
        skipped_hooks.update(set(skip_hooks or ()))
        if not unit_test:
            skipped_hooks.add("run-unit-tests")
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

        self.prepare_hooks(self.hooks)
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


def group_by_python_version(
    files: Set[Path], modules, git_util: GitUtil
) -> Tuple[Dict[str, Set], Set[Path]]:
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
        python_version = get_python_version(integration_script.docker_image)
        python_version_string = f"{python_version.major}.{python_version.minor}"
        code_files_to_include = code_files_to_include_for_path(
            integration_script, git_util
        )
        python_versions_to_files[
            python_version_string or DEFAULT_PYTHON2_VERSION
        ].update(
            integrations_scripts_mapping[code_file_path],
            {integration_script.path.relative_to(CONTENT_PATH)},
            integrations_scripts_mapping[code_file_path]
            | code_files_to_include
            | {integration_script.path}  # add the python including files here
        )
        # add_tmp_lint_files(content_repo=CONTENT_PATH,
        #                    modules=modules,
        #                    lint_files=list(code_files_to_include),
        #                    pack_path=integration_script.path.parent,
        #                    pack_type=TYPE_PYTHON if any(file.suffix == '.py' for file in code_files_to_include) else TYPE_PWSH).__enter__()

    if infra_files:
        python_versions_to_files[DEFAULT_PYTHON_VERSION].update(infra_files)

    if exclude_integration_script:
        logger.info(
            f"Skipping deprecated or powershell integrations or scripts: {join_files(exclude_integration_script, ', ')}"
        )
    return python_versions_to_files, exclude_integration_script


def code_files_to_include_for_path(content: BaseContent, git_util: GitUtil) -> set:
    parent = content.path.parent
    return {
        path.relative_to(CONTENT_PATH)
        for path in {
            parent / f
            for f in os.listdir(parent)
            if f.endswith(".py") or f.endswith(".ps1")
        }
    } & git_util.get_all_files()


def pre_commit_manager(
    input_files: Optional[Iterable[Path]] = None,
    staged_only: bool = False,
    git_diff: bool = False,
    all_files: bool = False,
    mode: Optional[PreCommitModes] = None,
    unit_test: bool = False,
    skip_hooks: Optional[List[str]] = None,
    validate: bool = False,
    format: bool = False,
    secrets: bool = False,
    verbose: bool = False,
    show_diff_on_failure: bool = False,
    sdk_ref: Optional[str] = None,
    dry_run: bool = False,
) -> Optional[int]:
    """Run pre-commit hooks .

    Args:
        input_files (Iterable[Path], optional): Input files to run pre-commit on. Defaults to None.
        staged_only (bool, optional): Whether to run on staged files only. Defaults to False.
        git_diff (bool, optional): Whether use git to determine precommit files. Defaults to False.
        all_files (bool, optional): Whether to run on all_files. Defaults to False.
        mode (PreCommitModes, optional): The mode to run pre-commit in. Defaults to None.
        test (bool, optional): Whether to run unit-tests. Defaults to False.
        skip_hooks (Optional[List[str]], optional): List of hooks to skip. Defaults to None.
        force_run_hooks (Optional[List[str]], optional): List for hooks to force run. Defaults to None.
        verbose (bool, optional): Whether run pre-commit in verbose mode. Defaults to False.
        show_diff_on_failure (bool, optional): Whether show git diff after pre-commit failure. Defaults to False.
        dry_run (bool, optional): Whether to run the pre-commit hooks in dry-run mode, which will only create the config file.

    Returns:
        int: Return code of pre-commit.
    """
    # We have imports to this module, however it does not exists in the repo.
    (CONTENT_PATH / "CommonServerUserPython.py").touch()

    if not any((input_files, staged_only, git_diff, all_files)):
        logger.info("No arguments were given, running on staged files and git changes.")
        git_diff = True
    git_util = GitUtil()
    files_to_run = preprocess_files(input_files, staged_only, git_diff, all_files, git_util)
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
    )


def preprocess_files(
    input_files: Optional[Iterable[Path]] = None,
    staged_only: bool = False,
    use_git: bool = False,
    all_files: bool = False,
    git_util=GitUtil(),
) -> Set[Path]:
    staged_files = git_util._get_staged_files()
    all_git_files = git_util.get_all_files().union(staged_files)
    if input_files:
        raw_files = set(input_files)
    elif staged_only:
        raw_files = staged_files
    elif use_git:
        raw_files = git_util._get_all_changed_files().union(staged_files)
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

    # convert to relative file to content path
    relative_paths = {
        file.relative_to(CONTENT_PATH) if file.is_absolute() else file
        for file in files_to_run
    }
    # filter out files that are not in the content git repo (e.g in .gitignore)
    return relative_paths & all_git_files
