from typing import Union

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    TextObject
from wcmatch.pathlib import Path


class Contributors(TextObject):
    def __init__(self, path: Union[Path, str]):
        self._path = path
        super().__init__(path)

    @property
    def path(self) -> Path:
        return self._path

    def type(self):
        return FileType.CONTRIBUTORS
