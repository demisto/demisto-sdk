from typing import List, Optional, Union

from demisto_sdk.commands.common.constants import PLAYBOOK
from demisto_sdk.commands.common.content.objects.pack_objects.base_pack_objects.yaml_pack_object import \
    YAMLPackObject
from demisto_sdk.commands.common.content.objects.pack_objects.readme.readme import \
    Readme
from packaging.version import LegacyVersion, Version
from wcmatch.pathlib import Path


class Playbook:
    def __init__(self, path: Union[Path, str]):
        self._object_type = YAMLPackObject(path, PLAYBOOK)

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

    @property
    def readme(self) -> Optional[Readme]:
        """YAML related Readme object.

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

    def dump(self, dest_dir: Optional[Union[str, Path]] = None, yaml: Optional[bool] = True,
             readme: Optional[bool] = False) -> List[Path]:
        """Dump YAMLContentObject.

        Args:
            dest_dir: Destination directory.
            yaml: True if to dump yml file (Used for unified object only).
            readme: True if to dump also related README.md.

        Returns:
            List[Path]: Path of new created files.
        """
        return self._object_type.dump(dest_dir, yaml, readme)
