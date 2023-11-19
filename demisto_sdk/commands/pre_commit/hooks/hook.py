import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Set

from demisto_sdk.commands.common.logger import logger


class Hook:
    def __init__(
        self,
        hook: dict,
        repo: dict,
        mode: str = "",
        all_files: bool = False,
        input_mode: bool = False,
    ) -> None:
        self.hooks: List[dict] = repo["hooks"]
        self.base_hook = deepcopy(hook)
        self.hook_index = self.hooks.index(self.base_hook)
        self.hooks.remove(self.base_hook)
        self.mode = mode
        self.all_files = all_files
        self.input_mode = input_mode
        self._set_properties()

    def prepare_hook(self, **kwargs):
        """
        This method should be implemented in each hook.
        Since we removed the base hook from the hooks list, we must add it back.
        So "self.hooks.append(self.base_hook)" or copy of the "self.base_hook" should be added anyway.
        """
        self.hooks.append(deepcopy(self.base_hook))

    def _set_files_on_hook(self, hook: dict, files) -> int:
        """

        Args:
            hook: mutates the hook with files returned from filter_files_matching_hook_config
            files: the list of files to set on the hook

        Returns: the number of files that ultimately are set on the hook. Use this to decide if to run the hook at all

        """
        files_to_run_on_hook = self.filter_files_matching_hook_config(files)
        hook["files"] = join_files(files_to_run_on_hook)

        return len(files_to_run_on_hook)

    def filter_files_matching_hook_config(self, files):
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
        ret = None
        if self.mode:
            ret = self.base_hook.get(f"{name}:{self.mode}")
        return ret or self.base_hook.get(name, default)

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
        for full_key in self.base_hook:
            key = full_key.split(":")[0]
            if hook.get(key):
                continue
            if prop := self._get_property(key):
                hook[key] = prop
        self.base_hook = hook


def join_files(files: Set[Path], separator: str = "|") -> str:
    """
    Joins a list of files into a single string using the specified separator.
    Args:
        files (list): A list of files to be joined.
        separator (str, optional): The separator to use when joining the files. Defaults to "|".
    Returns:
        str: The joined string.
    """
    return separator.join(map(str, files))


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
