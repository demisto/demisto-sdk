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
            1. "hello-world.yml" -> "reputation-hello-world.yml"
            2. "reputations.json" -> "reputations.json"

        Returns:
            str: Normalize file name.
        """
        normalize_file_name = self._path.name
        # Handle case "hello-world.yml"
        if not normalize_file_name.startswith(f'{OLD_INDICATOR_TYPE}'):
            normalize_file_name = f'{OLD_INDICATOR_TYPE}-{normalize_file_name}'

        return normalize_file_name
