from abc import abstractmethod
from typing import Any, Dict, Optional, Union

from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.constants import (
    CI_INJECTED_KEYS,
    IS_CONTENT_PRIVATE_KEY,
)
from demisto_sdk.commands.common.tools import get_id

from .general_object import GeneralObject


class DictionaryBasedObject(GeneralObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path, file_name_prefix)
        self._as_dict: Dict[str, Any] = {}

    @abstractmethod
    def _deserialize(self):
        pass

    def _contains_ci_injected_keys(self) -> bool:
        """Whether the file holds a CI-injected key at its top level (checked on raw bytes first, to avoid parsing)."""
        if IS_CONTENT_PRIVATE_KEY.encode() not in self._path.read_bytes():
            return False
        try:
            data = self.to_dict()
        except Exception:  # each format raises its own parse errors: keep the raw copy
            return False
        return isinstance(data, dict) and not CI_INJECTED_KEYS.isdisjoint(data)

    def _dict_without_ci_injected_keys(self) -> Any:
        """The object's dictionary, without the CI-injected keys."""
        data = self.to_dict()
        if isinstance(data, dict):
            return {
                key: value for key, value in data.items() if key not in CI_INJECTED_KEYS
            }
        return data

    def to_dict(self) -> dict:
        """Parse object file content to dictionary."""
        if not self._as_dict:
            self._deserialize()

        return self._as_dict

    def __getitem__(self, key: str) -> Any:
        """Get value by key from object file.

        Args:
            key: Key in file to retrieve.

        Returns:
            object: key value.

        Raises:
            ContentKeyError: If key not exists.
        """
        try:
            value = self.to_dict()[key]
        except KeyError:
            raise exc.ContentKeyError(self, self.path, key=key)

        return value

    def __setitem__(self, key: str, value: Any) -> None:
        self.to_dict()[key] = value

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Safe get value by key from object file.

        Args:
            key: Key in file to retrieve.
            default: Deafult value to return if key not exists - If not specified return None.

        Returns:
            object: key value.
        """
        try:
            value = self.__getitem__(key)
        except exc.ContentKeyError:
            value = default

        return value

    def get_id(self):
        return get_id(self.to_dict())

    def __contains__(self, item):
        return item in self._as_dict
