from abc import ABC, abstractmethod


class Hook(ABC):
    def __init__(self, repo: dict) -> None:
        self.repo = repo

    @abstractmethod
    def prepare_hook(self, **kwargs):
        return self.repo
