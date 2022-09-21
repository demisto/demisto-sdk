from abc import abstractmethod
from typing import Any, Dict, Optional, Union

from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc

from .general_object import GeneralObject


class DictionaryBasedObject(GeneralObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        super().__init__(path, file_name_prefix)
        self._as_dict: Dict[str, Any] = {}

    @abstractmethod
    def _deserialize(self):
        pass

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
        as_dict = self.to_dict()
        if 'commonfields' in as_dict.keys():
            return as_dict.get('commonfields', {}).get('id')
        elif 'dashboards_data' in as_dict.keys():
            return as_dict.get('dashboards_data', [{}])[0].get('global_id')
        elif 'templates_data' in as_dict.keys():
            return as_dict.get('templates_data', [{}])[0].get('global_id')
        elif 'global_rule_id' in as_dict.keys():
            return as_dict.get('global_rule_id')
        elif 'trigger_id' in as_dict.keys():
            return as_dict.get('trigger_id')
        elif 'content_global_id' in as_dict.keys():
            return as_dict.get('content_global_id')
        else:
            return as_dict.get('id')

    def __contains__(self, item):
        return item in self._as_dict
