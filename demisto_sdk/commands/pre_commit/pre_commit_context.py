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
PATH = Path(__file__).parents[0].resolve()
DEFAULT_PRE_COMMIT_TEMPLATE_PATH = PATH / PRECOMMIT_TEMPLATE_NAME

PRECOMMIT_FOLDER = CACHE_DIR / "pre-commit"
PRECOMMIT_CONFIG = PRECOMMIT_FOLDER / "config"
PRECOMMIT_CONFIG_MAIN_PATH = PRECOMMIT_CONFIG / "pre-commit-config-main.yaml"
ARTIFACTS_FOLDER = os.getenv("ARTIFACTS_FOLDER")
HOOK_LOG_PATH = Path(ARTIFACTS_FOLDER) / "pre-commit" if ARTIFACTS_FOLDER else None

# This has to be relative to content path so the docker will be able to write to it
PRE_COMMIT_FOLDER_SHARED = CONTENT_PATH / ".pre-commit"


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
    image_ref: Optional[str] = None
    docker_image: Optional[str] = None
    dry_run: bool = False
    pre_commit_template_path: Path = PRECOMMIT_TEMPLATE_PATH

    def __post_init__(self):
        """
        We initialize the hooks and all_files for later use.
        """
        shutil.rmtree(PRECOMMIT_FOLDER, ignore_errors=True)
        shutil.rmtree(PRE_COMMIT_FOLDER_SHARED, ignore_errors=True)
        PRECOMMIT_FOLDER.mkdir(parents=True)
        PRECOMMIT_CONFIG.mkdir()
        if HOOK_LOG_PATH:
            HOOK_LOG_PATH.mkdir(parents=True, exist_ok=True)
        self.precommit_template: dict = get_file_or_remote(
            self.pre_commit_template_path
        )
        remote_config_file = get_remote_file(str(self.pre_commit_template_path))
        if remote_config_file and remote_config_file != self.precommit_template:
            logger.info(
                f"Your local {PRECOMMIT_TEMPLATE_NAME} is not up to date to the remote one."
            )
        if not isinstance(self.precommit_template, dict):
            raise TypeError(
                f"Pre-commit template in {self.pre_commit_template_path} is not a dictionary."
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
            if obj is not None:
                support_level_to_files[obj.support].add(path)
        return support_level_to_files

    def _get_hooks(self, pre_commit_config: dict) -> dict:
        hooks = {}
        for repo in pre_commit_config.get("repos", []):
            new_hooks = []
            for hook in repo.get("hooks", []):
                if (not hook.get("log_file")) and HOOK_LOG_PATH:
                    hook["log_file"] = f"{HOOK_LOG_PATH}/{hook['id']}.log"
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
