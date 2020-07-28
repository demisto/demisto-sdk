from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstart_objects.json_content_object import JSONContentObject
from demisto_sdk.commands.common.constants import INDICATOR_TYPE, OLD_INDICATOR_TYPE


class Reputation(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INDICATOR_TYPE)


class OldReputation(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, OLD_INDICATOR_TYPE)
