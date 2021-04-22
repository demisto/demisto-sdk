from typing import Union

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.abstract_objects.text_object import \
    TextObject
from wcmatch.pathlib import Path


class ChangeLog(TextObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)

    def type(self):
        return FileType.CHANGELOG
