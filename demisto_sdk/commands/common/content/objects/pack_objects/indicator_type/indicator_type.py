from typing import Union

from demisto_sdk.commands.common.constants import (INDICATOR_TYPE,
                                                   OLD_INDICATOR_TYPE)
from demisto_sdk.commands.common.content.objects.base_objects.json_file import JsonFile
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.json_pack_mixins import \
    JsonPackMixin, JsonPackDumpMixin
from wcmatch.pathlib import Path


class IndicatorType(JsonFile, JsonPackMixin, JsonPackDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super(JsonFile).__init__(path=path, prefix=INDICATOR_TYPE)


class OldIndicatorType(JsonFile, JsonPackMixin, JsonPackDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super(JsonFile).__init__(path=path, prefix=OLD_INDICATOR_TYPE)

    # def normalize_file_name(self) -> str:
    #     """Add prefix to file name if not exists.
    #
    #     Examples:
    #         1. "hello-world.yml" -> "reputations.json"
    #         2. "reputations.json" -> "reputations.json"
    #
    #     Returns:
    #         str: Normalize file name.
    #     """
    #     return "reputations.json"
