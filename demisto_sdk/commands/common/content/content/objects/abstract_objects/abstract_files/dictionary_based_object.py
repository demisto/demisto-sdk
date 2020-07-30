from abc import abstractmethod
from typing import Any, Union, Optional

from wcmatch.pathlib import Path

from .general_object import GeneralObject


class DictionaryBasedObject(GeneralObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path, file_name_prefix)
        self._as_dict = {}

    @abstractmethod
    def _unserialize(self):
        pass

    def to_dict(self) -> dict:
        if not self._as_dict:
            self._unserialize()

        return self._as_dict

    def __getitem__(self, item: str) -> Any:
        return self.to_dict()[item]

    def get(self, item: str, default: Optional[Any] = None) -> Any:
        try:
            value = self.__getitem__(item)
        except KeyError:
            value = default

        return value
