from __future__ import annotations

import re
from typing import List, Optional, Union

from demisto_sdk.commands.common.content.objects.base_objects.json_file import \
    JsonFile
from demisto_sdk.commands.common.content.objects.pack_objects.readme.readme import \
    Readme
from demisto_sdk.commands.common.content.objects.utils import \
    normalize_file_name
from packaging.version import LegacyVersion, Version, parse
from wcmatch.pathlib import Path


class JsonPackReadmeMixin:
    @property
    def readme(self: JsonFile) -> Optional[Readme]:
        """JSON related Readme object.

        Returns:
            Readme object or None if Readme not found.
        """
        readme_file = next(self.path.parent.glob(patterns=fr'{re.escape(self.path.stem)}_README.md'), None)
        if readme_file:
            return Readme(readme_file)


class JsonPackVersionMixin:
    @property
    def from_version(self: JsonFile) -> Union[Version, LegacyVersion]:
        """Object from_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return parse(self.get('fromVersion', '0.0.0'))

    @property
    def to_version(self: JsonFile) -> Union[Version, LegacyVersion]:
        """Object to_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return parse(self.get('toVersion', '99.99.99'))


class JsonPackDumpMixin:
    def dump(self: Union[JsonPackReadmeMixin, JsonFile],
             dest_dir: Optional[Union[str, Path]] = None, readme: Optional[bool] = False) -> List[Path]:
        """Dump JSONContentObject.

        Args:
            dest_dir: Destination directory.
            readme: True if to dump also related README.md.

        Returns:
            List[Path]: Path of new created files.
        """
        created_files: List[Path] = []
        # Create directory and add prefix if not exists
        if not dest_dir:
            dest_file = self.path
        else:
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file = dest_dir / normalize_file_name(file_name=self.path.name, file_prefix=self._prefix)
        # Serialized dict to json
        created_files.append(self._serialize(dest_file))
        # Dump readme if requested and availble
        if readme and self.readme:
            created_files.extend(self.readme.dump(dest_dir))

        return created_files
