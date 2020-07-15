from shutil import copyfile
from typing import Union, Any, Optional
from packaging import version

from wcmatch.pathlib import Path
import ujson


class JSONObject:
    def __init__(self, path: Union[Path, str]):
        self._path = JSONObject._fix_path(path)
        self._json_as_dict = None
        self._prefix = ""

    @staticmethod
    def _fix_path(path: Union[Path, str]):
        path = Path(path)
        if path.is_dir():
            try:
                path = next(path.glob("*.json"))
            except Exception as e:
                raise BaseException(f"Unable to find yaml file in path {path}, Full error: {e}")

        return path

    @property
    def id(self):
        return self.__getitem__('id')

    @property
    def name(self):
        return self.__getitem__('name')

    @property
    def type(self):
        return self.__getitem__('type')

    @property
    def from_version(self):
        return version.parse(self.__getitem__("fromVersion"))

    @property
    def path(self) -> Path:
        return self._path

    @property
    def changelog(self) -> Path:
        return next(self._path.parent.glob(f"{self._path.stem}_CHANGELOG.md"), None)

    @property
    def readme(self):
        return next(self._path.parent.glob(f"{self._path.stem}_README.md"), None)

    def _unserialize(self) -> dict:
        try:
            json_to_dict = ujson.load(self._path.open())
        except Exception as e:
            raise BaseException(f"{self._path} is not valid json file, Full error: {e}")

        return json_to_dict

    def _serialize(self, dest):
        try:
            ujson.dump(self._json_as_dict, Path(dest).open())
        except Exception as e:
            raise BaseException(f"{self._path} unable to dump yaml object: {e}")

    def __getitem__(self, item) -> Any:
        if not self._json_as_dict:
            self._json_as_dict = self._unserialize()

        return self._json_as_dict[item]

    def __setitem__(self, key, value) -> None:
        if not self._json_as_dict:
            self._json_as_dict = self._unserialize()

        self._json_as_dict[key] = value

    def _dump_prefix(self, dest: Union[Path, str], suffix: Optional[str] = None):
        modified_path = dest
        if not modified_path.name.startswith(self._prefix):
            modified_path = modified_path.parent / f'{self._prefix}{modified_path.name}'
        if suffix:
            modified_path = modified_path.parent / f'{modified_path.stem}-{suffix}{modified_path.suffix}'

        return modified_path

    def dump(self, dest: Optional[Union[Path, str]] = None, change_log: bool = True, readme: bool = True):
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        # Create destination file name
        dest /= self._path.name
        # Fix file name
        dest = self._dump_prefix(dest)
        # Dump file if in memory else copy file
        if self._json_as_dict:
            self._serialize(dest)
        else:
            copyfile(self._path, dest)
        # Copy changelog
        if self.changelog and change_log:
            copyfile(self.changelog, dest.parent / f'{dest.stem}_CHANGELOG.md')
        # Copy readme
        if self.readme and readme:
            copyfile(str(self.readme), dest.parent / f'{dest.stem}_README.md')

