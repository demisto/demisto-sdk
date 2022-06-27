"""
abstract class for xsoar handlers (yaml, json, etc...)
"""

from abc import ABC, abstractmethod
from typing import IO, Any, AnyStr


class XSOAR_Handler(ABC):
    @abstractmethod
    def load(self, stream: IO[str]) -> Any:
        pass

    @abstractmethod
    def dump(self, data: AnyStr, fp: IO[str], **kwargs):
        pass

    @abstractmethod
    def dumps(self, obj: Any, **kwargs) -> str:
        pass
