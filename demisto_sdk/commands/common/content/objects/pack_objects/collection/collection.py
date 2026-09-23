from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import (
    YAMLContentObject,
)

COLLECTION = "collection"


class Collection(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, COLLECTION)

    def upload(self, client: demisto_client):
        pass

    def type(self):
        return FileType.COLLECTION
