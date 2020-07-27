import zipfile
from abc import ABC
from shutil import copytree, make_archive
from typing import Union, Optional
from zipfile import ZipFile

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstart_objects.abstract_data_objects.general_object import GeneralObject
from demisto_sdk.commands.common.constants import TOOL


class Tool(GeneralObject, ABC):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, TOOL)

    def dump(self, dest_dir: Optional[Union[Path, str]] = None, zip_file: bool = True):
        created_files = []
        if not dest_dir:
            dest_dir = self.path.parent
        normalize_dir_name = self._normalized_file_name()
        if zip_file:
            created_files.append(Path(make_archive(dest_dir / normalize_dir_name, 'zip', self._path)))
        else:
            created_files.extend(Path(copytree(src=self.path, dst=dest_dir / normalize_dir_name)).iterdir())

        return created_files
