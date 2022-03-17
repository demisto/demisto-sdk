"""
abstract class for xsoar handlers (yaml, json, etc...)
"""

from abc import ABC, abstractmethod


class XSOAR_Handler(ABC):
    @abstractmethod
    def load(self, stream):
        pass

    @abstractmethod
    def dump(self, data, stream, sort_keys=False):
        pass

    @abstractmethod
    def dumps(self, data, indent=None, sort_keys=False):
        pass
