from typing import Union

from wcmatch.pathlib import Path

import demisto_sdk.commands.common.content.errors as exc

from .general_object import GeneralObject


class TextObject(GeneralObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
        self._text = ""

    @staticmethod
    def _fix_path(path: Union[Path, str]):
        """Find and validate object path is valid.

        Rules:
            1. Path exists.
            2. Path is a file.

        Returns:
            Path: valid file path.

        Raises:
            ContentInitializeError: If path not valid.
        """
        path = Path(path)  # type: ignore
        if not (path.exists() and path.is_file()):
            raise exc.ContentInitializeError(TextObject, path)

        return path

    def _serialize(self, dest_dir: Path):
        """Dump string to text file

        TODO:
            1. Implement string serialize.
        """
        pass

    def _deserialize(self):
        """Load file content to string"""
        if not self._text:
            try:
                self._text = self.path.read_text()
            except OSError as e:
                raise exc.ContentSerializeError(self, self.path, str(e))

    def to_str(self):
        """File content as string.

        Returns:
            str: file content.
        """
        if not self._text:
            self._deserialize()

        return self._text
