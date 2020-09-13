from typing import Union

from demisto_sdk.commands.common.constants import (INCIDENT_FIELD,
                                                   INDICATOR_FIELD)
from demisto_sdk.commands.common.content.objects.base_objects.json_file import \
    JsonFile
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.json_pack_mixins import (
    JsonPackDumpMixin, JsonPackReadmeMixin, JsonPackVersionMixin)
from wcmatch.pathlib import Path


class IndicatorField(JsonFile, JsonPackReadmeMixin, JsonPackVersionMixin, JsonPackDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path=path, prefix=f'{INCIDENT_FIELD}-{INDICATOR_FIELD}')
