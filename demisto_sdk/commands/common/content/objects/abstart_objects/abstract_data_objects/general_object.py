from abc import abstractmethod
from typing import Optional, Union
from shutil import copyfile

from wcmatch.pathlib import Path


class GeneralObject(object):
    def __init__(self, path: Union[Path, str], file_name_prefix: str = ""):
        self._path = Path(path)
        self._changed = False
        self._prefix = file_name_prefix

    @property
    def path(self):
        return self._path

    @abstractmethod
    def _unserialize(self):
        pass

    @abstractmethod
    def _serialize(self, dest: Path) -> Path:
        pass

    def _normalized_file_name(self):
        file_normalized_name = self._path.name
        if self._path.suffix:
            file_normalized_name = ".".join(file_normalized_name.split('.')[:-1])
        if self._prefix and not file_normalized_name.startswith(f'{self._prefix}'):
            file_normalized_name = f'{self._prefix}-{file_normalized_name}'

        return f'{file_normalized_name}{self._path.suffix}'

    def _create_target_dump_dir(self, dest_dir: Optional[Union[Path, str]] = None) -> Path:
        if dest_dir:
            dest_dir = Path(dest_dir)
            if dest_dir.exists() and not Path(dest_dir).is_dir():
                raise BaseException("Destination must be a directory")
            else:
                dest_dir.mkdir(parents=True, exist_ok=True)
        else:
            dest_dir = self._path.parent

        return dest_dir

    def dump(self, dest_dir: Optional[Union[Path, str]] = None):
        created_files = []
        dest_file = self._create_target_dump_dir(dest_dir) / self._normalized_file_name()
        # If file changed should serialize to dest, else faster method - copyfile to dest
        if self._changed:
            created_files.append(self._serialize(dest_file))
        else:
            created_files.append(copyfile(src=self.path, dst=dest_file))

        return created_files
