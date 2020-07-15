from abc import abstractmethod
from shutil import copyfile
from typing import Union, Optional

from wcmatch.pathlib import Path, EXTMATCH

from yaml_object import YAMLObject


class CodeObject(YAMLObject):
    @property
    def code_path(self) -> Optional[Path]:
        patterns = [f"{self.yaml_path.stem}.@(ps1|js|py)"]
        return next(self._path.parent.glob(patterns=patterns, flags=EXTMATCH), None)

    @property
    def unittest_path(self) -> Optional[Path]:
        patterns = ["test_*.py", f"*_test.py"]
        return next(self._path.parent.glob(patterns=patterns))

    @property
    def png_path(self) -> Optional[Path]:
        patterns = [f"{self.yaml_path.stem}.png"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def description_path(self) -> Optional[Path]:
        patterns = [f"{self.yaml_path.stem}.md"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def readme_path(self) -> Optional[Path]:
        patterns = [f"README.md"]
        return next(self._path.parent.glob(patterns=patterns), None)

    def is_unify(self) -> bool:
        return self.code_path is None

    @abstractmethod
    def unify(self, dest):
        pass

    def dump(self, dest: Union[Path, str], change_log: bool = True, readme: bool = True):
        dest = Path(dest)
        dest.mkdir(parents=True, exist_ok=True)
        # Dump file if in memory else copy file
        if self._yaml_as_dict:
            # TODO create temp file - in json and yaml also
            self._serialize(self.yaml_path)
        # Unify if not unified
        if not self.is_unify():
            self.unify(dest)
        else:
            # Create destination file name
            dest /= self._path.name
            # Fix file name
            dest = self._dump_prefix(dest)
            copyfile(self._path, dest)
        # Copy changelog
        if self.changelog and change_log:
            copyfile(self.changelog, dest.parent / f'{dest.stem}_CHANGELOG.md')
        # Copy readme
        if self.readme and readme:
            copyfile(str(self.readme), dest.parent / f'{dest.stem}_README.md')

