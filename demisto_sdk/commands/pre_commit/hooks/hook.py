from abc import ABC, abstractmethod
from copy import deepcopy


class Hook(ABC):
    def __init__(self, hook: dict, repo: dict) -> None:
        self.hooks = repo["hooks"]
        self.base_hook = deepcopy(hook)
        self.hooks.remove(self.base_hook)

    @abstractmethod
    def prepare_hook(self, **kwargs):
        ...
