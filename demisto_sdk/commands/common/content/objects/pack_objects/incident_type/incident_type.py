from typing import Any, List, Optional, Union

from demisto_sdk.commands.common.constants import INCIDENT_TYPE
from demisto_sdk.commands.common.content.objects.pack_objects.base_pack_objects.json_pack_object import \
    JSONPackObject
from demisto_sdk.commands.common.content.objects.pack_objects.readme.readme import \
    Readme
from packaging.version import LegacyVersion, Version
from wcmatch.pathlib import Path


class IncidentType:
    def __init__(self, path: Union[Path, str]):
        self._object_type = JSONPackObject(path, INCIDENT_TYPE)

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

    @property
    def readme(self) -> Optional[Readme]:
        """JSON related Readme object.

        Returns:
            Readme object or None if Readme not found.
        """
        return self._object_type.readme

    @property
    def from_version(self) -> Union[Version, LegacyVersion]:
        """Object from_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return self._object_type.from_version

    @property
    def to_version(self) -> Union[Version, LegacyVersion]:
        """Object to_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return self._object_type.to_version

    def dump(self, dest_dir: Optional[Union[str, Path]] = None, readme: Optional[bool] = False) -> List[Path]:
        """Dump JSONContentObject.

        Args:
            dest_dir: Destination directory.
            readme: True if to dump also related README.md.

        Returns:
            List[Path]: Path of new created files.
        """
        return self._object_type.dump(dest_dir, readme)
