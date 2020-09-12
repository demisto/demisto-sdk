from typing import Union

from demisto_sdk.commands.common.constants import INCIDENT_FIELD
from demisto_sdk.commands.common.content.objects.base_objects.json_file import JsonFile
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.json_pack_mixins import \
    JsonPackMixin, JsonPackDumpMixin
from wcmatch.pathlib import Path


class IncidentField(JsonFile, JsonPackMixin, JsonPackDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super(JsonFile).__init__(path=path, prefix=INCIDENT_FIELD)
