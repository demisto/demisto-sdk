from typing import Union

from demisto_sdk.commands.common.constants import (INDICATOR_TYPE,
                                                   OLD_INDICATOR_TYPE)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


class IndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INDICATOR_TYPE)


class OldIndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, OLD_INDICATOR_TYPE)

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "reputations.json"
            2. "reputations.json" -> "reputations.json"

        Returns:
            str: Normalize file name.
        """
        return "reputations.json"
