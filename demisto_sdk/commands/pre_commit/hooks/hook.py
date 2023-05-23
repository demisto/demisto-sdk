from abc import ABC, abstractmethod
from typing import List
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from poetry.core.factory import Factory


class Hook(ABC):
    def __init__(self, hook: dict) -> None:
        self.hook = hook

    @abstractmethod
    def prepare_hook(self, **kwargs):
        return self.hook

    def additional_dependencies(self, group_name: str) -> List[str]:
        dependencies = Factory().create_poetry(CONTENT_PATH).package(group_name).dependencies
        return [p.to_pep_508() for p in dependencies]