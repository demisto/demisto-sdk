from typing import Union

from wcmatch.pathlib import Path

from ...abstract_objects import TextObject


class ReleaseNote(TextObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
