import re
from typing import List, Optional, Union

from packaging.version import LegacyVersion, Version, parse
from wcmatch.pathlib import EXTGLOB, Path

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
)
from demisto_sdk.commands.common.content.objects.abstract_objects import YAMLObject
from demisto_sdk.commands.common.content.objects.pack_objects.change_log.change_log import (
    ChangeLog,
)
from demisto_sdk.commands.common.content.objects.pack_objects.readme.readme import (
    Readme,
)


class YAMLContentObject(YAMLObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str):
        """YAML content object.

        Built from:
            1. <file_name>_README.md or README.md
            2. <file_name>_CHANGELOG.md or CHANGELOG.md
        """
        super().__init__(self._fix_path(path), file_name_prefix=file_name_prefix)
        self._readme: Optional[Readme] = None
        self._change_log: Optional[ChangeLog] = None

    @property
    def is_deprecated(self):
        return self.get("deprecated", False)

    @property
    def changelog(self) -> Optional[ChangeLog]:
        """YAML related ChangeLog object.

        Returns:
            Changelog object or None if Changelog not found.

        Notes:
            1. Should be deprecated in the future.
        """
        if not self._change_log:
            change_log_file = next(
                self.path.parent.glob(
                    patterns=rf"@(CHANGELOG.md|{re.escape(self.path.stem)}_CHANGELOG.md)",
                    flags=EXTGLOB,
                ),
                None,
            )
            if change_log_file:
                self._change_log = ChangeLog(change_log_file)

        return self._change_log

    @property
    def readme(self) -> Optional[Readme]:
        """YAML related Readme object.

        Returns:
            Readme object or None if Readme not found.
        """
        if not self._readme:
            readme_file = next(
                self.path.parent.glob(
                    patterns=rf"@(README.md|{re.escape(self.path.stem)}_README.md)",
                    flags=EXTGLOB,
                ),
                None,
            )
            if readme_file:
                self._readme = Readme(readme_file)

        return self._readme

    @property
    def from_version(self) -> Union[Version, LegacyVersion]:
        """Object from_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return parse(self.get("fromversion", DEFAULT_CONTENT_ITEM_FROM_VERSION))

    @property
    def to_version(self) -> Union[Version, LegacyVersion]:
        """Object to_version attribute.

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return parse(self.get("toversion", DEFAULT_CONTENT_ITEM_TO_VERSION))

    def dump(
        self,
        dest_dir: Optional[Union[str, Path]] = None,
        yaml: Optional[bool] = True,
        change_log: Optional[bool] = False,
        readme: Optional[bool] = False,
    ) -> List[Path]:
        """Dump YAMLContentObject.

        Args:
            dest_dir: Destination directory.
            yaml: True if to dump yml file (Used for unified object only).
            change_log: True if to dump also related CHANGELOG.md.
            readme: True if to dump also related README.md.

        Returns:
            List[Path]: Path of new created files.

        TODO:
            1. Handling case where object changed and need to be serialized.
        """
        created_files: List[Path] = []
        if yaml:
            created_files.extend(super().dump(dest_dir=dest_dir))
        # Dump changelog if requested and availble
        if change_log and self.changelog:
            created_files.extend(self.changelog.dump(dest_dir))
        # Dump readme if requested and availble
        if readme and self.readme:
            created_files.extend(self.readme.dump(dest_dir))

        return created_files
