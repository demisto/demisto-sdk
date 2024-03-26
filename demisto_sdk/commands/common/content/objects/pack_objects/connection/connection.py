from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import CANVAS, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)


class Connection(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, CANVAS)

    def type(self):
        return FileType.CONNECTION
