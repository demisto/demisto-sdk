"""
abstract class for xsoar handlers (yaml, json, etc...)
"""

from abc import ABC, abstractmethod
from typing import IO, Any, Union


class XSOAR_Handler(ABC):
    @abstractmethod
    def load(self, stream: IO[Union[str, bytes]]) -> Any:
        pass

    @abstractmethod
    def dump(self, data: Any, fp: IO[str], indent=0, sort_keys=False, **kwargs):
        pass

    @abstractmethod
    def dumps(self, obj: Any, indent=0, sort_keys=False, **kwargs) -> str:
        pass
