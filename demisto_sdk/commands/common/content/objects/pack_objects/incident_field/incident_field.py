from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstract_objects.abstract_content_files.json_content_object import JSONContentObject
from demisto_sdk.commands.common.constants import INCIDENT_FIELD


class IncidentField(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INCIDENT_FIELD)
