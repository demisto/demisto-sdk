from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.abstract_objects import \
    TextObject


class ReleaseNoteConfig(TextObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)

    def type(self):
        return FileType.RELEASE_NOTES_CONFIG
