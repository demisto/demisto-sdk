import json
from tempfile import NamedTemporaryFile
from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import INCIDENT_TYPE, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


class IncidentType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INCIDENT_TYPE)

    def upload(self, client: demisto_client):
        """
        Upload the incident type Container to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        if isinstance(self._as_dict, dict):
            incident_type_unified_data = [self._as_dict]
        else:
            incident_type_unified_data = self._as_dict

        with NamedTemporaryFile(suffix='.json') as incident_type_unified_file:
            incident_type_unified_file.write(bytes(json.dumps(incident_type_unified_data), 'utf-8'))
            incident_type_unified_file.seek(0)
            return client.import_incident_types_handler(file=incident_type_unified_file.name)

    def type(self):
        return FileType.INCIDENT_TYPE
