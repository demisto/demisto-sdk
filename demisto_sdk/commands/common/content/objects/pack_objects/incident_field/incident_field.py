from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import INCIDENT_FIELD
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


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
        return client.import_incident_fields(file=self.path)
