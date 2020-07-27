from abc import ABC, abstractmethod
from typing import Any, Union, Optional

from wcmatch.pathlib import Path

from general_object import GeneralObject


class DictionaryBasedObject(GeneralObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path, file_name_prefix)
        self._as_dict = {}

    @abstractmethod
    def _unserialize(self):
        pass

    @abstractmethod
    def _serialize(self, dest: Path):
        pass

    def __getitem__(self, item: str) -> Any:
        if not self._as_dict:
            self._unserialize()

        return self._as_dict[item]

    def __setitem__(self, key: str, value: Any) -> None:
        if not self._as_dict:
            self._unserialize()
        self._as_dict[key] = value
        self._changed = True

    def get(self, item: str, default: Optional[Any] = None):
        try:
            value = self.__getitem__(item)
        except KeyError:
            value = default

        return value

    def to_dict(self) -> dict:
        if not self._as_dict:
            self._unserialize()

        return self._as_dict
