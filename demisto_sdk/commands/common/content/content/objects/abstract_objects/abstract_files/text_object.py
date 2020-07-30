from typing import Union

from wcmatch.pathlib import Path

from .general_object import GeneralObject


class TextObject(GeneralObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(self._fix_path(path))
        self._text = ""

    @staticmethod
    def _fix_path(path: Union[Path, str]):
        path = Path(path)
        if path.is_dir():
            try:
                path = next(path.glob([f"*.*"]))
            except StopIteration as e:
                raise BaseException(f"Unable to find text file in path {path}, Full error: {e}")
        elif not (path.is_file() or path.suffix in ["json"]):
            raise BaseException(f"Unable to find text file in path {path}")

        return path

    def to_str(self):
        if not self._text:
            self._unserialize()

        return self._text

    def _unserialize(self):
        if not self._text:
            try:
                self._text = self.path.read_text()
            except IOError as e:
                raise BaseException(f"Unable to unserialize text from {self.path}, Full error: {e}")
