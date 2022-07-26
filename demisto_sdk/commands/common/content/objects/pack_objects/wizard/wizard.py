from pathlib import Path
from typing import Union

from demisto_sdk.commands.common.constants import WIZARD, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)


class Wizard(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, WIZARD)

    def type(self):
        return FileType.WIZARD
