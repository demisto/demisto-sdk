from typing import Union

from demisto_sdk.commands.common.content.objects.abstract_objects import \
    JSONObject
from wcmatch.pathlib import Path


class PackMetaData(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
