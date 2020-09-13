from typing import Any, List, Optional, Union

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.content.objects.base_objects.bytes_file import \
    BytesFile
from demisto_sdk.commands.common.content.objects.base_objects.json_file import \
    JsonFile
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import \
    YamlFile
from demisto_sdk.commands.common.content.objects.utils import \
    normalize_file_name
from wcmatch.pathlib import Path


class FileDumpMixin:
    def dump(self: Union[JsonFile, YamlFile, BytesFile], dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        """Dump unmodified object.

        Args:
            dest_dir: destination directory to dump object

        Returns:
            List[Path]: List of path created in given directory.
        """
        created_files: List[Path] = []
        if not dest_dir:
            dest_file = self.path.parent
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)

        dest_file = dest_dir / normalize_file_name(file_name=self.path.name, file_prefix=self._prefix)

        created_files.append(self._serialize(dest_file))

        return created_files


class DictBaseFileMixin:
    @property
    def path(self: Union[JsonFile, YamlFile]):
        return self._path

    def __dict__(self: Union[JsonFile, YamlFile]) -> dict:
        """Parse object file content to dictionary."""
        return self._unserialize()

    def __getitem__(self: Union[JsonFile, YamlFile], key: str) -> Any:
        """Get value by key from object file.

        Args:
            key: Key in file to retrieve.

        Returns:
            object: key value.

        Raises:
            ContentKeyError: If key not exists.
        """
        try:
            value = self.__dict__()[key]
        except KeyError:
            raise exc.ContentKeyError(self, self.path, key=key)

        return value

    def __setitem__(self: Union[JsonFile, YamlFile], key: Any, value: Any) -> Any:
        """Get value by key from object file.

        Args:
            key: Key in file to retrieve.

        Returns:
            object: key value.

        Raises:
            ContentKeyError: If key not exists.
        """
        try:
            value = self.__dict__()[key] = value
            self._data_changed = True
        except KeyError:
            raise exc.ContentKeyError(self, self.path, key=key)

        return value

    def get(self: Union[JsonFile, YamlFile], key: str, default: Optional[Any] = None) -> Any:
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
