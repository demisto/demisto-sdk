from abc import ABC, abstractmethod
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class Hook(ABC):
    def __init__(
        self,
        hook: dict,
        repo: dict,
        mode: str = "",
        all_files: bool = False,
        input_mode: bool = False,
        to_delete: tuple = (),
    ) -> None:
        self.hooks: List[dict] = repo["hooks"]
        self.base_hook = deepcopy(hook)
        self.hook_index = self.hooks.index(self.base_hook)
        self.hooks.remove(self.base_hook)
        self.mode = mode
        self.all_files = all_files
        self.input_mode = input_mode
        self._set_properties(hook={}, to_delete=to_delete)

    @abstractmethod
    def prepare_hook(self, **kwargs):
        """
        This method should be implemented in each hook.
        Since we removed the base hook from the hooks list, we must add it back.
        So "self.hooks.append(self.base_hook)" or copy of the "self.base_hook" should be added anyway.
        """
        self.hooks.append(deepcopy(self.base_hook))

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
            ret = self.base_hook.get(f"{name}:{self.mode.value}")
        return ret or self.base_hook.get(name, default)

    def _set_properties(self, hook, to_delete=()):
        """
        Will alter the new hook, setting the properties that don't need unique behavior
        For any propery x, if x isn't already defined, x will be set according to the mode provided.
        For example, given an input
        args: 123
        args:nightly 456
        if the mode provided is nightly, args will be set to 456. Otherwise, the default (key with no :) will be taken
        Args:
            hook: the hook to modify
            to_delete: keys on the demisto config that we dont want to pass to precommit
        """
        for full_key in self.base_hook:
            key = full_key.split(":")[0]
            if hook.get(key) or key in to_delete:
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
