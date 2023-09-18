from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Set


class Hook(ABC):
    def __init__(
        self, hook: dict, repo: dict, all_files: bool = False, input_mode: bool = False
    ) -> None:
        self.hooks = repo["hooks"]
        self.base_hook = deepcopy(hook)
        self.hooks.remove(self.base_hook)
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


def create_or_update_list_in_dict(dict: Dict[str, list], key: str, value: Any) -> None:
    """
    Creates or updates a list in a dictionary.

    This function takes a dictionary, a key, and a value as input.
    If the key already exists in the dictionary, the value is appended to the existing list.
    If the key does not exist, a new key-value pair is added to the dictionary.

    Args:
        dict (Dict[str, list]): The dictionary in which to create or update the list.
        key (str): The key to use for the list in the dictionary.
        value (Any): The value to append to the list.

    Returns:
        None
    """
    if key in dict:
        dict[key].append(value)
    else:
        dict[key] = [value]
