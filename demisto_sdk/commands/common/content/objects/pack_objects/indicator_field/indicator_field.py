from tempfile import NamedTemporaryFile
from typing import Union

import demisto_client
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import (
    INCIDENT_FIELD,
    INDICATOR_FIELD,
    FileType,
)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import (
    JSONContentObject,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json


class IndicatorField(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INDICATOR_FIELD)

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "incidentfield-indicatorfield-hello-world.yml"
            2. "indicatorfield-hello-world.yml" -> "incidentfield-indicatorfield-hello-world.yml"

        Returns:
            str: Normalize file name.
        """
        normalize_file_name = self._path.name
        # Handle case where "incidentfield-*hello-world.yml"
        if normalize_file_name.startswith(
            f"{INCIDENT_FIELD}-"
        ) and not normalize_file_name.startswith(
            f"{INCIDENT_FIELD}-{INDICATOR_FIELD}-"
        ):
            normalize_file_name = normalize_file_name.replace(
                f"{INCIDENT_FIELD}-", f"{INCIDENT_FIELD}-{INDICATOR_FIELD}-"
            )
        else:
            # Handle case where "indicatorfield-*hello-world.yml"
            if normalize_file_name.startswith(f"{INDICATOR_FIELD}-"):
                normalize_file_name = normalize_file_name.replace(
                    f"{INDICATOR_FIELD}-", f"{INCIDENT_FIELD}-{INDICATOR_FIELD}-"
                )
            # Handle case where "*hello-world.yml"
            else:
                normalize_file_name = (
                    f"{INCIDENT_FIELD}-{INDICATOR_FIELD}-{normalize_file_name}"
                )

        return normalize_file_name

    def upload(self, client: demisto_client):
        """
        Upload the indicator field to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        # The incident field import endpoint also accepts indicator fields
        if isinstance(self._as_dict, dict):
            indicator_fields_unified_data = {"incidentFields": [self._as_dict]}
        else:
            indicator_fields_unified_data = {"incidentFields": self._as_dict}

        with NamedTemporaryFile(suffix=".json") as indicator_fields_unified_file:
            indicator_fields_unified_file.write(
                bytes(json.dumps(indicator_fields_unified_data), "utf-8")
            )
            indicator_fields_unified_file.seek(0)
            return client.import_incident_fields(
                file=indicator_fields_unified_file.name
            )

    def type(self):
        return FileType.INDICATOR_FIELD
