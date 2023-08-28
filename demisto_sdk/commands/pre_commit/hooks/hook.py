from abc import ABC, abstractmethod


class Hook(ABC):
    def __init__(self, hook: dict, repo: dict) -> None:
        self.hook = hook
        self.repo = repo

    @abstractmethod
    def prepare_hook(self, **kwargs):
        ...
