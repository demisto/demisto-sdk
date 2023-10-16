import re

from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from demisto_sdk.commands.common.constants import PreCommitModes
from demisto_sdk.commands.common.logger import logger


class Hook(ABC):
    def __init__(
            self,
            hook: dict,
            repo: dict,
            mode: Optional[PreCommitModes] = None,
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

    @abstractmethod
    def prepare_hook(self, **kwargs):
        """
        This method should be implemented in each hook.
        Since we removed the base hook from the hooks list, we must add it back.
        So "self.hooks.append(self.base_hook)" or copy of the "self.base_hook" should be added anyway.
        """
        ...

    def set_files_on_hook(self, hook: dict, files) -> int:
        """
        Mutates a hook, setting a regex for file exact match on the hook
        according to the file's *file* and *exclude* properties
        Args:
            hook: The hook to mutate
            files: The files to set on the hook
        Returns:
            The number of files set
        """
        include_pattern = None
        exclude_pattern = None
        try:

            if files_reg := hook.get("files"):
                include_pattern = re.compile(files_reg)
            if exclude_reg := hook.get("exclude"):
                exclude_pattern = re.compile(exclude_reg)
        except re.error:
            logger.info('regex not set correctly on hook. Ignoring')

        files_to_run_on_hook = {
            file
            for file in [str(file) for file in files]  # todo had a check that file is git file. needed?
            if (not include_pattern or re.search(include_pattern, file))  # include all if not defined
               and (not exclude_pattern or not re.search(exclude_pattern, file))}  # only exclude if defined
        hook["files"] = join_files(files_to_run_on_hook)

        # hook.pop("exclude", None)
        return len(files_to_run_on_hook)


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
