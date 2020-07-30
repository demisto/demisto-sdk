from typing import Union

from wcmatch.pathlib import Path

from ...abstract_objects.abstract_files.text_object import TextObject


class ChangeLog(TextObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
