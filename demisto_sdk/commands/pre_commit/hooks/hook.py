from abc import ABC, abstractmethod
from copy import deepcopy


class Hook(ABC):
    def __init__(self, hook: dict, repo: dict) -> None:
        self.hooks = repo["hooks"]
        self.base_hook = deepcopy(hook)
        self.hooks.remove(self.base_hook)

    @staticmethod
    def _join_files(files: list, separator: str = "|") -> str:
        """
        Joins a list of files into a single string using the specified separator.
        Args:
            files (list): A list of files to be joined.
            separator (str, optional): The separator to use when joining the files. Defaults to "|".
        Returns:
            str: The joined string.
        """
        return separator.join(map(str, files))

    @abstractmethod
    def prepare_hook(self, **kwargs):
        """
        This method should be implemented in each hook.
        Since we removed the base hook from the hooks list, we must add it back.
        So "self.hooks.append(self.base_hook)" or copy of the "self.base_hook" should be added anyway.
        """
        ...
