from abc import abstractmethod
from shutil import copyfile
from typing import List, Optional, Union

from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc


class GeneralObject(object):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        """ Abstract object for represent objects in content.

        Args:
            path: Valid path for object. (Determined by object type - JSON/YAML/TEXT)
            file_name_prefix: File prefix for fixing it if needed <prefix>-<original-file-name>.
        """
        self._path = self._fix_path(path)
        self._prefix = file_name_prefix

    @staticmethod
    @abstractmethod
    def _fix_path(path: Union[Path, str]) -> Path:
        """Find and validate object path is valid."""
        pass

    @property
    def path(self) -> Path:
        return self._path

    @abstractmethod
    def _unserialize(self):
        """Implementation for unserializing object - JSON/YAML/TEXT"""
        pass

    @abstractmethod
    def _serialize(self, dest_dir: Path):
        """Implementation for serializing object - JSON/YAML/TEXT"""
        pass

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "<prefix>-hello-world.yml"

        Returns:
            str: Normalize file name.
        """
        normalize_file_name = self._path.name
        if self._prefix and not normalize_file_name.startswith(f'{self._prefix}-'):
            normalize_file_name = f'{self._prefix}-{normalize_file_name}'

        return normalize_file_name

    def _create_target_dump_dir(self, dest_dir: Optional[Union[Path, str]] = None) -> Path:
        """Create destination directory, Destination must be valid directory, If not specified dump in
         path of origin object.

        Args:
            dest_dir: destination directory to dump object.

        Returns:
            Path: Destionaion directory.

        Raises:
            DumpContentObjectError: If not valid directory path - not directory or not exists.
        """
        if dest_dir:
            dest_dir = Path(dest_dir)
            if dest_dir.exists() and not Path(dest_dir).is_dir():
                raise exc.ContentDumpError(self, self._path, "Destiantion is not valid directory path")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
        else:
            dest_dir = self._path.parent

        return dest_dir

    def dump(self, dest_dir: Optional[Union[Path, str]] = None) -> List[Path]:
        """Dump unmodified object.

        Args:
            dest_dir: destination directory to dump object

        Returns:
            List[Path]: List of path created in given directory.

        TODO:
            1. Implement dump of modified object.
        """
        dest_file = self._create_target_dump_dir(dest_dir) / self.normalize_file_name()

        return [copyfile(src=self.path, dst=dest_file)]

    def type(self):
        return None
