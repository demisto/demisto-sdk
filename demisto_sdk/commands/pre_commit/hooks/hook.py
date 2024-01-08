import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from packaging.version import Version

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.pre_commit.hooks.utils import get_property
from demisto_sdk.commands.pre_commit.pre_commit_context import PreCommitContext

PROPERTIES_TO_DELETE = {"needs"}


class Hook:
    def __init__(
        self,
        hook: dict,
        repo: dict,
        context: PreCommitContext,
    ) -> None:
        self.hooks: List[dict] = repo["hooks"]
        self.base_hook = deepcopy(hook)
        self.hook_index = self.hooks.index(self.base_hook)
        self.hooks.remove(self.base_hook)
        self.mode = context.mode
        self.all_files = context.all_files
        self.input_mode = bool(context.input_files)
        self.context = context
        self._set_properties()
        self.exclude_irrelevant_files()

    def prepare_hook(self):
        """
        This method should be implemented in each hook.
        Since we removed the base hook from the hooks list, we must add it back.
        So "self.hooks.append(self.base_hook)" or copy of the "self.base_hook" should be added anyway.
        """
        self.hooks.append(deepcopy(self.base_hook))

    def exclude_irrelevant_files(self):
        self._exclude_hooks_by_version()
        self._exclude_hooks_by_support_level()

    def _set_files_on_hook(
        self, hook: dict, files: Iterable[Path], should_filter: bool = True
    ) -> int:
        """

        Args:
            hook: mutates the hook with files returned from filter_files_matching_hook_config
            files: the list of files to set on the hook

        Returns: the number of files that ultimately are set on the hook. Use this to decide if to run the hook at all

        """
        files_to_run_on_hook = set(files)
        if should_filter:
            files_to_run_on_hook = self.filter_files_matching_hook_config(files)
        hook["files"] = join_files(files_to_run_on_hook)
        return len(files_to_run_on_hook)

    def filter_files_matching_hook_config(
        self,
        files: Iterable[Path],
    ):
        """
        returns files that should be run in this hook according to the provided regexs in files and exclude
        Note, we could easily support glob syntax here too in the future.
        (or whatever function precomit uses internally)
        Args:
            files: The files to set on the hook
        Returns:
            The number of files set
        """
        include_pattern = None
        exclude_pattern = None
        try:

            if files_reg := self.base_hook.get("files"):
                include_pattern = re.compile(files_reg)
            if exclude_reg := self.base_hook.get("exclude"):
                exclude_pattern = re.compile(exclude_reg)
        except re.error:
            logger.info("regex not set correctly on hook. Ignoring")

        return {
            file
            for file in files
            if (
                not include_pattern or re.search(include_pattern, str(file))
            )  # include all if not defined
            and (not exclude_pattern or not re.search(exclude_pattern, str(file)))
        }  # only exclude if defined

    def _get_property(self, name, default=None):
        """
        Will get the given property from the base hook, taking mode into account
        Args:
            name: the key to get from the config
            default: the default value to return
        Returns: The value from the base hook
        """
        return get_property(self.base_hook, self.mode, name, default=default)

    def _set_properties(self):
        """
        For any property x, if x isn't already defined, x will be set according to the mode provided.
        For example, given an input
        args: 123
        args:nightly 456
        if the mode provided is nightly, args will be set to 456. Otherwise, the default (key with no :) will be taken.
        Update the base_hook accordingly.
        """
        hook: Dict = {}
        keys_to_delete = []
        for full_key in self.base_hook:
            key = full_key.split(":")[0]
            if hook.get(key):
                continue
            if key in PROPERTIES_TO_DELETE:
                keys_to_delete.append(key)
            if (prop := self._get_property(key)) is not None:
                hook[key] = prop
        for key in keys_to_delete:
            hook.pop(key, None)
        self.base_hook = hook

    def _exclude_hooks_by_version(self) -> None:
        """
        This function excludes the files that are not supported by the hook, according to the hook min_version property.
        """
        min_version = self._get_property("min_py_version")
        self.base_hook.pop("min_py_version", None)
        if not min_version:
            return
        files_to_exclude: Set[Path] = set()

        for version, paths in self.context.python_version_to_files.items():
            if Version(version) < Version(min_version):
                files_to_exclude.update(path for path in paths)
        if files_to_exclude:
            join_files_string = join_files(files_to_exclude)
            if self.base_hook.get("exclude"):
                self.base_hook["exclude"] += f"|{join_files_string}"
            else:
                self.base_hook["exclude"] = join_files_string

    def _exclude_hooks_by_support_level(self) -> None:
        """This function excludes the hooks that are not supported by the support level of the file."""
        support_levels = self._get_property("exclude_support_level")
        self.base_hook.pop("exclude_support_level", None)
        if not support_levels:
            return
        files_to_exclude: Set[Path] = set()
        for support_level in support_levels:
            files_to_exclude.update(
                path for path in self.context.support_level_to_files[support_level]
            )
        if files_to_exclude:
            join_files_string = join_files(files_to_exclude)
            if self.base_hook.get("exclude"):
                self.base_hook["exclude"] += f"|{join_files_string}"
            else:
                self.base_hook["exclude"] = join_files_string


def join_files(files: Set[Path], separator: str = "|") -> str:
    """
    Joins a list of files into a single string using the specified separator.
    Args:
        files (list): A list of files to be joined.
        separator (str, optional): The separator to use when joining the files. Defaults to "|".
    Returns:
        str: The joined string.
    """
    return separator.join(
        str(file) if Path(file).is_file() else f"{str(file)}{os.sep}" for file in files
    )


def safe_update_hook_args(hook: Dict, value: Any) -> None:
    """
    Updates the 'args' key in the given hook dictionary with the provided value.
    Args:
        hook (Dict): The hook dictionary to update.
        value (Any): The value to append to the 'args' key.
    Returns:
        None
    """
    args_key = "args"
    if args_key in hook:
        hook[args_key].append(value)
    else:
        hook[args_key] = [value]
