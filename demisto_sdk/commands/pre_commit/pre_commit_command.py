import itertools
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property, partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from packaging.version import Version

from demisto_sdk.commands.common.constants import (
    DEFAULT_PYTHON_VERSION,
    INTEGRATIONS_DIR,
    PACKS_FOLDER,
    SCRIPTS_DIR,
)
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH, PYTHONPATH
from demisto_sdk.commands.common.cpu_count import cpu_count
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_file_or_remote,
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
from demisto_sdk.commands.pre_commit.hooks.system import SystemHook
from demisto_sdk.commands.pre_commit.hooks.validate_format import ValidateFormatHook

IS_GITHUB_ACTIONS = string_to_bool(os.getenv("GITHUB_ACTIONS"), False)

PRECOMMIT_TEMPLATE_NAME = ".pre-commit-config_template.yaml"
PRECOMMIT_TEMPLATE_PATH = CONTENT_PATH / PRECOMMIT_TEMPLATE_NAME
PRECOMMIT_FOLDER = CONTENT_PATH / ".pre-commit"
PRECOMMIT_CONFIG = PRECOMMIT_FOLDER / "config"
PRECOMMIT_CONFIG_MAIN_PATH = PRECOMMIT_CONFIG / ".pre-commit-config-main.yaml"
PRECOMMIT_DOCKER_CONFIGS = PRECOMMIT_CONFIG / "docker"
SOURCERY_CONFIG_PATH = CONTENT_PATH / ".sourcery.yaml"

SKIPPED_HOOKS = {"format", "validate", "secrets"}

INTEGRATION_SCRIPT_REGEX = re.compile(r"^Packs/.*/(?:Integrations|Scripts)/.*.yml$")


@dataclass
class PreCommitContext:
    """This class is responsible of running pre-commit hooks."""

    input_files: Optional[List[Path]]
    all_files: bool
    mode: str
    language_version_to_files_with_objects: Dict[
        str, Set[Tuple[Path, Optional[IntegrationScript]]]
    ]
    run_hook: Optional[str] = None
    skipped_hooks: Set[str] = field(default_factory=set)
    run_docker_hooks: bool = True
    dry_run: bool = False

    def __post_init__(self):
        """
        We initialize the hooks and all_files for later use.
        """
        shutil.rmtree(PRECOMMIT_FOLDER, ignore_errors=True)
        PRECOMMIT_FOLDER.mkdir()
        PRECOMMIT_CONFIG.mkdir()
        PRECOMMIT_DOCKER_CONFIGS.mkdir()

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
        self.hooks = self._get_hooks(self.precommit_template)
        self.hooks_need_docker = self._hooks_need_docker()

    @cached_property
    def files_to_run_with_objects(
        self,
    ) -> Set[Tuple[Path, Optional[IntegrationScript]]]:
        return set(
            itertools.chain.from_iterable(
                self.language_version_to_files_with_objects.values()
            )
        )

    @cached_property
    def files_to_run(self) -> Set[Path]:
        return {file for file, _ in self.files_to_run_with_objects}

    @cached_property
    def language_to_files(self) -> Dict[str, Set[Path]]:
        return {
            version: {path for path, _ in paths_with_objects}
            for version, paths_with_objects in self.language_version_to_files_with_objects.items()
        }

    @cached_property
    def python_version_to_files(self) -> Dict[str, Set[Path]]:
        return {
            version: {path for path, _ in paths_with_objects}
            for version, paths_with_objects in self.language_version_to_files_with_objects.items()
            if version not in {"javascript", "powershell"}
        }

    @cached_property
    def support_level_to_files(self) -> Dict[str, Set[Path]]:
        support_level_to_files = defaultdict(set)
        for path, obj in self.files_to_run_with_objects:
            if obj:
                support_level_to_files[obj.support_level].add(path)
        return support_level_to_files

    @staticmethod
    def _get_repos(pre_commit_config: dict) -> dict:
        repos = {}
        for repo in pre_commit_config["repos"]:
            repos[repo["repo"]] = repo
        return repos

    def _get_hooks(self, pre_commit_config: dict) -> dict:
        hooks = {}
        for repo in pre_commit_config.get("repos", []):
            new_hooks = []
            for hook in repo.get("hooks", []):
                if not self.run_docker_hooks and hook["id"].endswith("in-docker"):
                    continue
                if (self.run_hook and hook["id"] in self.run_hook) or (
                    not self.run_hook
                    and hook["id"] not in self.skipped_hooks
                    and not Hook.get_property(hook, self.mode, "skip")
                ):
                    needs = Hook.get_property(hook, self.mode, "needs")
                    if needs and any(need not in hooks for need in needs):
                        continue
                    new_hooks.append(hook)
                    hooks[hook["id"]] = {"repo": repo, "hook": hook}

                repo["hooks"] = new_hooks

        return hooks

    def _hooks_need_docker(self) -> Set[str]:
        """
        Get all the hook ids that needs docker based on the "needs" property
        """
        return {
            hook_id
            for hook_id, hook in self.hooks.items()
            if (needs := hook["hook"].pop("needs", None))
            and any("in-docker" in need for need in needs)
        }

    def _get_docker_and_no_docker_hooks(
        self, local_repo: dict
    ) -> Tuple[List[dict], List[dict]]:
        """This function separates the docker and no docker hooks of a local repo

        Args:
            local_repo (dict): The local repo

        Returns:
            Tuple[List[dict], List[dict]]: The first item is the list of docker hooks, the second is the list of no docker hooks
        """
        local_repo_hooks = local_repo["hooks"]
        docker_hooks = [hook for hook in local_repo_hooks if "in-docker" in hook["id"]]
        no_docker_hooks = [
            hook for hook in local_repo_hooks if "in-docker" not in hook["id"]
        ]
        return docker_hooks, no_docker_hooks

    def _filter_hooks_need_docker(self, repos: dict) -> dict:
        """
        This filters the pre-commit config file the hooks that needed docker, so we will be able to execute them after the docker hooks are finished
        """
        full_hooks_need_docker = {}
        for repo, repo_dict in repos.items():
            hooks = []
            for hook in repo_dict["hooks"]:
                if hook["id"] not in self.hooks_need_docker:
                    hooks.append(hook)
                else:
                    full_hooks_need_docker[hook["id"]] = {
                        "repo": repo_dict,
                        "hook": hook,
                    }
            repo_dict["hooks"] = hooks
        return full_hooks_need_docker

    def _update_hooks_needs_docker(self, hooks_needs_docker: dict):
        """
        This is to populate the pre-commit config file only for hooks that needs docker
        This is needed because we need to execute this after all docker hooks are finished
        """
        self.precommit_template["repos"] = []
        for _, hook in hooks_needs_docker.items():
            repos = {repo["repo"] for repo in self.precommit_template["repos"]}
            repo_in_hook = hook["repo"]["repo"]
            if repo_in_hook not in repos:
                hook["repo"]["hooks"] = []
                self.precommit_template["repos"].append(hook["repo"])
                repo = self.precommit_template["repos"][-1]
            else:
                repo = next(
                    repo
                    for repo in self.precommit_template["repos"]
                    if repo["repo"] == repo_in_hook
                )
            repo["hooks"].append(hook["hook"])


class PreCommitRunner:
    @staticmethod
    def prepare_hooks(pre_commit_context: PreCommitContext) -> None:
        hooks = pre_commit_context.hooks
        if "pycln" in hooks:
            PyclnHook(**hooks.pop("pycln"), context=pre_commit_context).prepare_hook()
        if "ruff" in hooks:
            RuffHook(**hooks.pop("ruff"), context=pre_commit_context).prepare_hook()
        if "mypy" in hooks:
            MypyHook(**hooks.pop("mypy"), context=pre_commit_context).prepare_hook()
        if "sourcery" in hooks:
            SourceryHook(
                **hooks.pop("sourcery"), context=pre_commit_context
            ).prepare_hook()
        if "validate" in hooks:
            ValidateFormatHook(
                **hooks.pop("validate"), context=pre_commit_context
            ).prepare_hook()
        if "format" in hooks:
            ValidateFormatHook(
                **hooks.pop("format"), context=pre_commit_context
            ).prepare_hook()
        [
            DockerHook(**hooks.pop(hook_id), context=pre_commit_context).prepare_hook()
            for hook_id in hooks.copy()
            if hook_id.endswith("in-docker")
        ]
        # iterate the rest of the hooks
        for hook_id in hooks.copy():
            # this is used to handle the mode property correctly
            Hook(**hooks.pop(hook_id), context=pre_commit_context).prepare_hook()
        # get the hooks again because we want to get all the hooks, including the once that already prepared
        hooks = pre_commit_context._get_hooks(pre_commit_context.precommit_template)
        system_hooks = [
            hook_id
            for hook_id, hook in hooks.items()
            if hook["hook"].get("language") == "system"
        ]
        for hook_id in system_hooks.copy():
            SystemHook(**hooks[hook_id], context=pre_commit_context).prepare_hook()

    @staticmethod
    def run_hooks(
        index: Optional[int],
        precommit_env: dict,
        verbose: bool = False,
        stdout: Optional[int] = subprocess.PIPE,
    ):
        """This function runs the pre-commit process and waits until finished.
        We run this function in multithread.

        Args:
            index (Optional[int]): The index of the docker hook. if None, runs main pre-commit config
            precommit_env (dict): The pre-commit environment variables
            verbose (bool, optional): Whether print verbose output. Defaults to False.
            stdout (Optional[int], optional): The way to handle stdout. Defaults to subprocess.PIPE.

        Returns:
            int: return code - 0 if hooks passed, 1 if failed
        """
        if index is None:
            process = PreCommitRunner._run_pre_commit_process(
                PRECOMMIT_CONFIG_MAIN_PATH, precommit_env, verbose, stdout
            )
        else:
            process = PreCommitRunner._run_pre_commit_process(
                PRECOMMIT_DOCKER_CONFIGS / f"pre-commit-config-docker-{index}.yaml",
                precommit_env,
                verbose,
                stdout,
            )
        if process.stdout:
            logger.info(process.stdout)
        if process.stderr:
            logger.error(process.stderr)
        return process.returncode

    @staticmethod
    def _run_pre_commit_process(
        path: Path,
        precommit_env: dict,
        verbose: bool,
        stdout=None,
        command: Optional[List[str]] = None,
    ) -> subprocess.CompletedProcess:
        """Runs a process of pre-commit

        Args:
            path (Path): Pre commit path
            precommit_env (dict): Environment variables set on pre-commit
            verbose (bool): whether to print verbose output
            stdout (optional): use `subprocess.PIPE` to capture stdout. Use None to print it. Defaults to None.
            command (Optional[List[str]], optional): The pre-commit command to run. Defaults to None.

        Returns:
            _type_: _description_
        """
        if command is None:
            command = ["run", "-a"]
        return subprocess.run(
            list(
                filter(
                    None,
                    [
                        sys.executable,
                        "-m",
                        "pre_commit",
                        *command,
                        "-c",
                        str(path),
                        "-v" if verbose and "run" in command else "",
                    ],
                )
            ),
            env=precommit_env,
            cwd=CONTENT_PATH,
            stdout=stdout,
            stderr=stdout,
            universal_newlines=True,
        )

    @staticmethod
    def run(
        pre_commit_context: PreCommitContext,
        precommit_env: dict,
        verbose: bool,
        show_diff_on_failure: bool,
    ) -> int:
        if pre_commit_context.mode:
            logger.info(
                f"[yellow]Running pre-commit hooks in `{pre_commit_context.mode}` mode.[/yellow]"
            )
        if pre_commit_context.run_hook:
            logger.info(f"[yellow]Running hook {pre_commit_context.run_hook}[/yellow]")
        repos = pre_commit_context._get_repos(pre_commit_context.precommit_template)
        local_repo = repos["local"]
        (
            docker_hooks,
            no_docker_hooks,
        ) = pre_commit_context._get_docker_and_no_docker_hooks(local_repo)
        local_repo["hooks"] = no_docker_hooks
        full_hooks_need_docker = pre_commit_context._filter_hooks_need_docker(repos)

        num_processes = cpu_count()
        logger.info(f"Pre-Commit will use {num_processes} processes")
        write_dict(PRECOMMIT_CONFIG_MAIN_PATH, pre_commit_context.precommit_template)
        # first, run the hooks without docker hooks
        stdout = subprocess.PIPE if docker_hooks else None
        PreCommitRunner._run_pre_commit_process(
            PRECOMMIT_CONFIG_MAIN_PATH,
            precommit_env,
            verbose,
            command=["install-hooks"],
        )
        for i, hook in enumerate(docker_hooks):
            pre_commit_context.precommit_template["repos"] = [local_repo]
            local_repo["hooks"] = [hook]
            path = PRECOMMIT_DOCKER_CONFIGS / f"pre-commit-config-docker-{i}.yaml"
            write_dict(path, data=pre_commit_context.precommit_template)

        # the threads will run in separate process and will wait for completion
        with ThreadPool(num_processes) as pool:
            results = pool.map(
                partial(
                    PreCommitRunner.run_hooks,
                    precommit_env=precommit_env,
                    verbose=verbose,
                    stdout=stdout,
                ),
                [None] + list(range(len(docker_hooks))),
            )
        return_code = int(any(results))
        if pre_commit_context.hooks_need_docker:
            # run hooks that needs docker after all the docker hooks finished
            pre_commit_context._update_hooks_needs_docker(full_hooks_need_docker)
            path = PRECOMMIT_CONFIG_MAIN_PATH.with_name(
                f"{PRECOMMIT_CONFIG_MAIN_PATH.stem}-needs.yaml"
            )
            write_dict(path, pre_commit_context.precommit_template)
            process_needs_docker = PreCommitRunner._run_pre_commit_process(
                path, precommit_env, verbose=verbose
            )

            return_code = return_code or process_needs_docker.returncode

        if return_code and show_diff_on_failure:
            logger.info(
                "Pre-Commit changed the following. If you experience this in CI, please run `demisto-sdk pre-commit`"
            )
            git_diff = subprocess.run(
                ["git", "--no-pager", "diff", "--no-ext-diff"],
                stdout=subprocess.PIPE,
                universal_newlines=True,
            )
            logger.info(git_diff.stdout)
        return return_code

    @staticmethod
    def prepare_and_run(
        pre_commit_context: PreCommitContext,
        verbose: bool = False,
        show_diff_on_failure: bool = False,
        exclude_files: Optional[Set[Path]] = None,
        dry_run: bool = False,
    ) -> int:

        ret_val = 0
        pre_commit_context.dry_run = dry_run
        precommit_env = os.environ.copy()
        precommit_env["PYTHONPATH"] = ":".join(str(path) for path in PYTHONPATH)
        # The PYTHONPATH should be the same as the PYTHONPATH, but without the site-packages because MYPY does not support it
        precommit_env["MYPYPATH"] = ":".join(
            str(path) for path in sorted(PYTHONPATH) if "site-packages" not in str(path)
        )
        precommit_env["DEMISTO_SDK_CONTENT_PATH"] = str(CONTENT_PATH)
        precommit_env["SYSTEMD_COLORS"] = "1"  # for colorful output
        precommit_env["PRE_COMMIT_COLOR"] = "always"

        if pre_commit_context.all_files:
            logger.info("Running pre-commit on all files")

        else:
            for (
                python_version,
                changed_files_by_version,
            ) in pre_commit_context.python_version_to_files.items():
                changed_files_string = "\n".join(
                    sorted(str(file) for file in changed_files_by_version)
                )
                logger.info(
                    f"Running pre-commit with Python {python_version} on:\n{changed_files_string}"
                )

        PreCommitRunner.prepare_hooks(pre_commit_context)

        if pre_commit_context.all_files:
            pre_commit_context.precommit_template[
                "exclude"
            ] += f"|{join_files(exclude_files or set())}"
        else:
            pre_commit_context.precommit_template["files"] = join_files(
                pre_commit_context.files_to_run
            )

        if dry_run:
            write_dict(
                PRECOMMIT_CONFIG_MAIN_PATH, data=pre_commit_context.precommit_template
            )
            logger.info(
                f"Dry run, skipping pre-commit.\nConfig file saved to {PRECOMMIT_CONFIG_MAIN_PATH}"
            )
            return ret_val
        ret_val = PreCommitRunner.run(
            pre_commit_context, precommit_env, verbose, show_diff_on_failure
        )
        return ret_val


def group_by_language(
    files: Set[Path],
) -> Tuple[Dict[str, Set[Tuple[Path, Optional[IntegrationScript]]]], Set[Path]]:
    """This function groups the files to run pre-commit on by the python version.

    Args:
        files (Set[Path]): files to run pre-commit on.

    Raises:
        Exception: If invalid files were given.

    Returns:
        Dict[str, set]: The files grouped by their python version, and a set of excluded paths
    """
    integrations_scripts_mapping = defaultdict(set)
    infra_files = []
    for file in files:
        if file.is_dir():
            continue
        if (
            set(file.parts) & {INTEGRATIONS_DIR, SCRIPTS_DIR}
            and file.parts[0] == PACKS_FOLDER  # this is relative path so it works
        ):
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
            if not code_file_path.is_dir():
                continue
            integrations_scripts_mapping[code_file_path].add(file)
        else:
            infra_files.append(file)

    language_to_files: Dict[str, Set] = defaultdict(set)
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
            # we exclude deprecate integrations and scripts from pre-commit.
            # the reason we maintain this set is for performance when running with --all-files. It is much faster to exclude.
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
            language = f"{version.major}.{version.minor}"
        else:
            language = integration_script.type
        language_to_files[language].update(
            {
                (path, integration_script)
                for path in integrations_scripts_mapping[code_file_path]
            },
            {(integration_script.path.relative_to(CONTENT_PATH), integration_script)},
        )

    if infra_files:
        language_to_files[DEFAULT_PYTHON_VERSION].update(
            [(infra, None) for infra in infra_files]
        )

    if exclude_integration_script:
        logger.info(
            f"Skipping deprecated integrations or scripts: {join_files(exclude_integration_script, ', ')}"
        )
    return language_to_files, exclude_integration_script


def pre_commit_manager(
    input_files: Optional[Iterable[Path]] = None,
    staged_only: bool = False,
    commited_only: bool = False,
    git_diff: bool = False,
    all_files: bool = False,
    mode: str = "",
    skip_hooks: Optional[List[str]] = None,
    validate: bool = False,
    format: bool = False,
    secrets: bool = False,
    verbose: bool = False,
    show_diff_on_failure: bool = False,
    dry_run: bool = False,
    run_docker_hooks: bool = True,
    run_hook: Optional[str] = None,
) -> int:
    """Run pre-commit hooks .

    Args:
        input_files (Iterable[Path], optional): Input files to run pre-commit on. Defaults to None.
        staged_only (bool, optional): Whether to run on staged files only. Defaults to False.
        commited_only (bool, optional): Whether to run on commited files only. Defaults to False.
        git_diff (bool, optional): Whether use git to determine precommit files. Defaults to False.
        all_files (bool, optional): Whether to run on all_files. Defaults to False.
        mode (str): The mode to run pre-commit in. Defaults to empty str.
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
        return 0

    language_to_files_with_objects, exclude_files = group_by_language(files_to_run)
    if not language_to_files_with_objects:
        logger.info("No files to run pre-commit on, skipping pre-commit.")
        return 0

    skipped_hooks: set = SKIPPED_HOOKS
    skipped_hooks.update(set(skip_hooks or ()))
    if validate and "validate" in skipped_hooks:
        skipped_hooks.remove("validate")
    if format and "format" in skipped_hooks:
        skipped_hooks.remove("format")
    if secrets and "secrets" in skipped_hooks:
        skipped_hooks.remove("secrets")

    pre_commit_context = PreCommitContext(
        list(input_files) if input_files else None,
        all_files,
        mode,
        language_to_files_with_objects,
        run_hook,
        skipped_hooks,
        run_docker_hooks,
    )
    return PreCommitRunner.prepare_and_run(
        pre_commit_context,
        verbose,
        show_diff_on_failure,
        exclude_files,
        dry_run,
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
            if file.suffix in (".py", ".ps1"):
                if file.suffix == ".py":
                    test_file = file.with_name(f"{file.stem}_test.py")
                else:
                    test_file = file.with_name(f"{file.stem}.Tests.ps1")
                if test_file.exists():
                    files_to_run.add(test_file)

    # convert to relative file to content path
    relative_paths = {
        file.relative_to(CONTENT_PATH) if file.is_absolute() else file
        for file in files_to_run
    }
    # filter out files that are not in the content git repo (e.g in .gitignore)
    return relative_paths & all_git_files
