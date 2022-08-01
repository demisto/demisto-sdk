import os
import zipfile
from shutil import copytree
from typing import List, Optional, Union

from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc
from demisto_sdk.commands.common.constants import TOOL
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    GeneralObject


class AgentTool(GeneralObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, TOOL)

    @staticmethod
    def _fix_path(path: Union[Path, str]) -> Path:
        """Find and validate object path is valid.

        Rules:
            1. Path exists.
            2. One of the following options:
                a. Path is a file -> If it is file, path is parent directory.
                b. Path is directory.

        Returns:
            Path: valid file path.

        Raises:
            ContentInitializeError: If path not valid.
        """
        path = Path(path)
        if not path.exists():
            raise exc.ContentInitializeError(AgentTool, path)
        elif path.is_file():
            path = path.parent

        return path

    def _serialize(self, dest_dir: Path, zip: bool = True) -> List[Path]:
        """ Serialize Agent tool.

        Args:
            dest_dir: Destination directory.
            zip: True if agent tool should be zipped when serializing.

        Notes:
            1. Agent tool should be zip when deleivered for installation.
            2. Comment should be added to zip when its system agent tool - not contribution.

        Returns:
            List[Path]: Path of new created files.
        """
        created_files: List[Path] = []
        if zip:
            zip_file = (dest_dir / self.normalize_file_name()).with_suffix('.zip')
            created_files.append(zip_file)
            with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.comment = b'{ "system": true }'
                for root, _, files in os.walk(self.path):
                    for file_name in files:
                        zipf.write(os.path.join(root, file_name), file_name)
        else:
            created_files.extend(Path(copytree(src=self.path, dst=dest_dir / self.normalize_file_name())).iterdir())

        return created_files

    def _unserialize(self):
        """Currently no usage"""
        pass

    def dump(self, dest_dir: Optional[Union[Path, str]] = None, zip: bool = True):
        """ Dump Agent tool.
        Args:
            dest_dir: Destination directory.
            zip: True if agent tool should be zipped when serializing.

        Returns:
            List[Path]: Path of new created files.
        """
        dest_dir = self._create_target_dump_dir(dest_dir)

        return self._serialize(dest_dir)
