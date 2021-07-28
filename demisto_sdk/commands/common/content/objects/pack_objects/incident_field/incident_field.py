import json
from tempfile import NamedTemporaryFile
from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import INCIDENT_FIELD, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject


class IncidentField(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INCIDENT_FIELD)

    def upload(self, client: demisto_client):
        """
        Upload the incident field to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        if isinstance(self._as_dict, dict):
            incident_fields_unified_data = {'incidentFields': [self._as_dict]}
        else:
            incident_fields_unified_data = {'incidentFields': self._as_dict}

        with NamedTemporaryFile(suffix='.json') as incident_fields_unified_file:
            incident_fields_unified_file.write(bytes(json.dumps(incident_fields_unified_data), 'utf-8'))
            incident_fields_unified_file.seek(0)
            return client.import_incident_fields(file=incident_fields_unified_file.name)

    def type(self):
        return FileType.INCIDENT_FIELD
