from typing import Union

from demisto_sdk.commands.common.constants import REPORT, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


class Report(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, REPORT)

    def type(self):
        return FileType.REPORT
