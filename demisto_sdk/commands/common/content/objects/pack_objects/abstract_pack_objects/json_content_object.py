import re
from typing import List, Optional, Union

from packaging.version import Version
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (
    DEFAULT_CONTENT_ITEM_FROM_VERSION,
    DEFAULT_CONTENT_ITEM_TO_VERSION,
)
from demisto_sdk.commands.common.content.objects.abstract_objects import JSONObject
from demisto_sdk.commands.common.content.objects.pack_objects.change_log.change_log import (
    ChangeLog,
)
from demisto_sdk.commands.common.content.objects.pack_objects.readme.readme import (
    Readme,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_json
from demisto_sdk.commands.prepare_content.prepare_upload_manager import (
    PrepareUploadManager,
)


class JSONContentObject(JSONObject):
    def __init__(self, path: Union[Path, str], file_name_prefix):
        """JSON content object.

        Built from:
            1. <file_name>_README.md
            2. <file_name>_CHANGELOG.md
        """
        super().__init__(self._fix_path(path), file_name_prefix)
        self._readme: Optional[Readme] = None
        self._change_log: Optional[ChangeLog] = None

    @property
    def changelog(self) -> Optional[ChangeLog]:
        """JSON related ChangeLog object.

        Returns:
            Changelog object or None if Changelog not found.

        Notes:
            1. Should be deprecated in the future.
        """
        if not self._change_log:
            change_log_file = next(
                self.path.parent.glob(
                    patterns=rf"{re.escape(self.path.stem)}_CHANGELOG.md"
                ),
                None,
            )
            if change_log_file:
                self._change_log = ChangeLog(change_log_file)

        return self._change_log

    @property
    def readme(self) -> Optional[Readme]:
        """JSON related Readme object.

        Returns:
            Readme object or None if Readme not found.
        """
        if not self._readme:
            readme_file = next(
                self.path.parent.glob(
                    patterns=rf"{re.escape(self.path.stem)}_README.md"
                ),
                None,
            )
            if readme_file:
                self._readme = Readme(readme_file)

        return self._readme

    @property
    def from_version(self) -> Version:
        """Object from_version attribute.
        Note: On Packaging>=v23, Version('') is no longer equivalent to Version("0.0.0"), which is why we do the `or 0.0.0`

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return Version(self.get("fromVersion") or DEFAULT_CONTENT_ITEM_FROM_VERSION)

    @property
    def to_version(self) -> Version:
        """Object to_version attribute.
        Note: On Packaging>=v23, Version('') is no longer equivalent to Version("0.0.0"), which is why we do the `or 0.0.0`

        Returns:
            version: Version object which able to be compared with other Version object.

        References:
            1. Version object - https://github.com/pypa/packaging
            2. Attribute info - https://xsoar.pan.dev/docs/integrations/yaml-file#version-and-tests
        """
        return Version(
            self.get("toVersion", DEFAULT_CONTENT_ITEM_TO_VERSION) or "0.0.0"
        )

    def dump(
        self,
        dest_dir: Optional[Union[str, Path]] = None,
        change_log: Optional[bool] = False,
        readme: Optional[bool] = False,
    ) -> List[Path]:
        """Dump JSONContentObject.

        Args:
            dest_dir: Destination directory.
            change_log: True if to dump also related CHANGELOG.md.
            readme: True if to dump also related README.md.

        Returns:
            List[Path]: Path of new created files.

        TODO:
            1. Handling case where object changed and need to be serialized.
        """
        created_files: List[Path] = []

        try:
            created_files.extend(
                self._unify(
                    dest_dir=self._create_target_dump_dir(dest_dir=dest_dir),
                    output=self.normalize_file_name(),
                )
            )
            logger.debug(f"Successfully unified {self.path} {self.type()}")
        except Exception as e:
            logger.debug(
                f"Could not unify {self.path} {self.type()} because of error {e}, dumping without unifying"
            )
            created_files.extend(super().dump(dest_dir=dest_dir))

        # Dump changelog if requested and available
        if change_log and self.changelog:
            created_files.extend(self.changelog.dump(dest_dir))
        # Dump readme if requested and available
        if readme and self.readme:
            created_files.extend(self.readme.dump(dest_dir))
        return created_files

    def is_file_structure_list(self) -> bool:
        """
        Checks whether the content of the file has a structure of a list.
        Assuming the file is a valid json file, use this to determine whether the file holds a list of values or a dictionary.
        """
        data = get_json(str(self.path))
        return isinstance(data, list)

    def _unify(
        self, dest_dir: Optional[Union[Path, str]] = None, output: str = ""
    ) -> List[Path]:
        """Unify JSONBasedContentObject in destination dir.

        Args:
            dest_dir: Destination directory, if not provided the destination directory will be the current working dir.
            output: output suffix to add the destination directory.

        Returns:
            List[Path]: List of new created unified json files.
        """
        if dest_dir is None:
            dest_dir = ""

        # Unify step
        return [
            Path(
                str(
                    PrepareUploadManager.prepare_for_upload(
                        input=self.path,
                        output=Path(dest_dir, output),  # type: ignore[arg-type]
                    )
                )
            )
        ]
