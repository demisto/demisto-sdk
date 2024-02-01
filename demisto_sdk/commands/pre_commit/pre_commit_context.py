import itertools
import os
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from demisto_sdk.commands.common.constants import CACHE_DIR
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    get_file_or_remote,
    get_remote_file,
    string_to_bool,
)
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.pre_commit.hooks.utils import get_property

IS_GITHUB_ACTIONS = string_to_bool(os.getenv("GITHUB_ACTIONS"), False)

PRECOMMIT_TEMPLATE_NAME = ".pre-commit-config_template.yaml"
PRECOMMIT_TEMPLATE_PATH = CONTENT_PATH / PRECOMMIT_TEMPLATE_NAME
PRECOMMIT_FOLDER = CACHE_DIR / "pre-commit"
PRECOMMIT_CONFIG = PRECOMMIT_FOLDER / "config"
PRECOMMIT_CONFIG_MAIN_PATH = PRECOMMIT_CONFIG / "pre-commit-config-main.yaml"
PRECOMMIT_DOCKER_CONFIGS = PRECOMMIT_CONFIG / "docker"


@dataclass
class PreCommitContext:
    """This class is saving the context run of pre-commit hooks.
    This data is shared between all hooks"""

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
        PRECOMMIT_FOLDER.mkdir(parents=True)
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
        logger.debug(f"PreCommitContext: {self.asdict()}")

    def asdict(self):
        dct = self.__dict__.copy()
        dct.pop("language_version_to_files_with_objects", None)
        dct["python_version_to_files"] = self.python_version_to_files
        return dct

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
                if (self.run_hook and self.run_hook in hook["id"]) or (
                    not self.run_hook
                    and hook["id"] not in self.skipped_hooks
                    and not get_property(hook, self.mode, "skip")
                ):
                    needs = get_property(hook, self.mode, "needs")
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
