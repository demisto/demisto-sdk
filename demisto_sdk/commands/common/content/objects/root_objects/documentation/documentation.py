from typing import Any, List, Optional, Union

from demisto_sdk.commands.common.constants import DOCUMENTATION
from demisto_sdk.commands.common.content.objects.base_objects.json_object import \
    JSONObject
from wcmatch.pathlib import Path


class Documentation:
    def __init__(self, path: Union[Path, str]):
        self._object_type = JSONObject(path, DOCUMENTATION)

    @property
    def path(self) -> Path:
        return self._object_type.path

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "<prefix>-hello-world.yml"

        Returns:
            str: Normalize file name.
        """
        return self._object_type.normalize_file_name()

    def to_dict(self) -> dict:
        """Parse object file content to dictionary."""
        return self._object_type.to_dict()

    def __getitem__(self, key: str) -> Any:
        """Get value by key from object file.

        Args:
            key: Key in file to retrieve.

        Returns:
            object: key value.

        Raises:
            ContentKeyError: If key not exists.
        """
        return self._object_type.__getitem__(key)

    def get(self, key: str, default: Optional[Any] = None) -> Any:
        """Safe get value by key from object file.

        Args:
            key: Key in file to retrieve.
            default: Deafult value to return if key not exists - If not specified return None.

        Returns:
            object: key value.
        """
        return self._object_type.get(key, default)

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        """Dump unmodified object.

        Args:
            dest_dir: destination directory to dump object

        Returns:
            List[Path]: List of path created in given directory.
        """
        return self._object_type.dump(dest_dir)
