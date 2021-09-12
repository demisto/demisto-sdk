from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import GENERIC_TYPE, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject


class GenericType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, GENERIC_TYPE)

    def upload(self, client: demisto_client):
        pass

    def type(self):
        return FileType.GENERIC_TYPE
