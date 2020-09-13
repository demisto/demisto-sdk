import re
from typing import List, Optional, Union

from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import \
    YamlFile
from demisto_sdk.commands.common.content.objects.pack_objects.readme.readme import \
    Readme
from packaging.version import LegacyVersion, Version, parse
from wcmatch.pathlib import EXTGLOB, Path

from ...utils import normalize_file_name


class YamlPackReamdeMixin:
    @property
    def readme(self: YamlFile) -> Optional[Readme]:
        """YAML related Readme object.

        Returns:
            Readme object or None if Readme not found.
        """

        readme_file = next(self.path.parent.glob(patterns=fr'@(README.md|{re.escape(self.path.stem)}_README.md)',
                                                 flags=EXTGLOB), None)
        if readme_file:
            return Readme(readme_file)


class YamlPackVersionsMixin:
    @property
    def from_version(self: YamlFile) -> Union[Version, LegacyVersion]:
        """Object from_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return parse(self.get('fromversion', '0.0.0'))

    @property
    def to_version(self: YamlFile) -> Union[Version, LegacyVersion]:
        """Object to_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return parse(self.get('toversion', '99.99.99'))


class YamlPackDumpMixin:
    def dump(self: Union[YamlFile, YamlPackReamdeMixin],
             dest_dir: Optional[Union[str, Path]] = None, readme: Optional[bool] = False) -> List[Path]:
        """Dump YAMLContentObject.

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
