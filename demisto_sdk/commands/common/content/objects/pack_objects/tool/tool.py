import zipfile
from abc import ABC
from shutil import copytree
from typing import Union, Optional
from demisto_sdk.commands.common.tools import zip_tool

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstract_objects.abstract_files.general_object import GeneralObject
from demisto_sdk.commands.common.constants import TOOL


class Tool(GeneralObject, ABC):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, TOOL)

    def dump(self, dest_dir: Optional[Union[Path, str]] = None, zip_file: bool = True):
        created_files = []
        dest_dir = self._create_target_dump_dir(dest_dir)
        if not dest_dir:
            dest_dir = self.path.parent
        normalize_dir_name = self._normalized_file_name()
        if zip_file:
            created_files.append(zip_tool(self._path, dest_dir / normalize_dir_name))
        else:
            created_files.extend(Path(copytree(src=self.path, dst=dest_dir / normalize_dir_name)).iterdir())

        return created_files
