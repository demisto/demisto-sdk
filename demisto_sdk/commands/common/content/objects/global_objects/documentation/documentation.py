from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstract_objects.abstract_files.json_object import JSONObject
from demisto_sdk.commands.common.constants import DOCUMENTATION


class Documentation(JSONObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, DOCUMENTATION)
