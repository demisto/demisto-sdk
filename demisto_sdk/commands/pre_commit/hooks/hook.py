from abc import ABC, abstractmethod


class Hook(ABC):
    def __init__(self, hook: dict) -> None:
        self.hook = hook

    @abstractmethod
    def prepare_hook(self, **kwargs):
        return self.hook
