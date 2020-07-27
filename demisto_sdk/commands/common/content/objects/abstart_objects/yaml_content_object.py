from typing import Union, Optional
import re

from wcmatch.pathlib import Path, EXTGLOB
from packaging.version import parse, Version
from ruamel.yaml.scalarstring import FoldedScalarString

from demisto_sdk.commands.common.content.objects.abstart_objects.abstract_data_objects.yaml_object import YAMLObject
from demisto_sdk.commands.common.content.objects.readme.readme import Readme
from demisto_sdk.commands.common.content.objects.change_log.change_log import ChangeLog


class YAMLConentObject(YAMLObject):
    def __init__(self, path: Union[Path, str], file_name_prefix: str):
        super().__init__(self._fix_path(path), file_name_prefix=file_name_prefix)
        self._readme: Optional[Readme] = None
        self._change_log: Optional[ChangeLog] = None

    @property
    def changelog(self) -> Optional[ChangeLog]:
        if not self._change_log:
            change_log_file = next(self.path.parent.glob(patterns=fr'@(CHANGELOG.md|{re.escape(self.path.stem)}_CHANGELOG.md)',
                                                         flags=EXTGLOB), None)
            if change_log_file:
                self._change_log = ChangeLog(change_log_file)

        return self._change_log

    @property
    def readme(self) -> Optional[Readme]:
        if not self._readme:
            readme_file = next(self.path.parent.glob(patterns=fr'@(README.md|{re.escape(self.path.stem)}_README.md)',
                                                     flags=EXTGLOB), None)
            if readme_file:
                self._readme = Readme(readme_file)

        return self._readme

    def _pre_dump(self):
        for key in ['script', 'detaileddescription']:
            if key in self:
                self[key] = FoldedScalarString(self.get(key))

    @property
    def from_version(self) -> Version:
        return parse(self.get('fromversion', '0.0.0'))

    @from_version.setter
    def from_version(self, value: Union[str, Version]):
        self.__setitem__('fromversion', str(value))

    @property
    def to_version(self) -> Version:
        return parse(self.get('toversion', '99.99.99'))

    @to_version.setter
    def to_version(self, value: Union[str, Version]):
        self.__setitem__('toversion', str(value))

    def dump(self, dest_dir: Optional[Union[str, Path]] = None, change_log: Optional[bool] = True,
             readme: Optional[bool] = True):
        created_files = []
        created_files.extend(super().dump(dest_dir=dest_dir))
        # Dump changelog if requested and availble
        if change_log and self.changelog:
            created_files.extend(self.changelog.dump(dest_dir))
        # Dump readme if requested and availble
        if readme and self.readme:
            created_files.extend(self.readme.dump(dest_dir))

        return created_files
