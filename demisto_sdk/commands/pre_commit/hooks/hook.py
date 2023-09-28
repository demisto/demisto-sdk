from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Set


class Hook(ABC):
    def __init__(
        self,
        hook: dict,
        repo: dict,
        mode: str = None,
        all_files: bool = False,
        input_mode: bool = False,
    ) -> None:
        self.hooks = repo["hooks"]
        self.base_hook = deepcopy(hook)
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
