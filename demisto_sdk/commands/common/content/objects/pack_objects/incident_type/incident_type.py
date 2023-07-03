import os
import platform
from tempfile import NamedTemporaryFile
from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import INCIDENT_TYPE, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json


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

        is_win_os = platform.system() == "Windows"

        # Set delete to False if a Windows operating system is detected
        # On Windows operating systems, NamedTemporaryFile objects cannot be
        # opened a second time while open in a context manager
        with NamedTemporaryFile(
            suffix=".json",
            delete=not is_win_os,
        ) as incident_type_unified_file:
            incident_type_unified_file.write(
                bytes(json.dumps(incident_type_unified_data), "utf-8")
            )
            incident_type_unified_file.seek(0)

            filename = incident_type_unified_file.name

            if not is_win_os:
                return client.import_incident_types_handler(file=filename)

        # This section only runs if Windows is the detected operating system
        res = client.import_incident_types_handler(file=filename)
        # Delete the NamedTemporaryFile object
        os.remove(filename)
        return res

    def type(self):
        return FileType.INCIDENT_TYPE
