from typing import Union

from demisto_sdk.commands.common.constants import (INCIDENT_FIELD,
                                                   INDICATOR_FIELD)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


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
        if normalize_file_name.startswith(f'{INCIDENT_FIELD}-') and \
                not normalize_file_name.startswith(f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-'):
            normalize_file_name = normalize_file_name.replace(f'{INCIDENT_FIELD}-',
                                                              f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-')
        else:
            # Handle case where "indicatorfield-*hello-world.yml"
            if normalize_file_name.startswith(f'{INDICATOR_FIELD}-'):
                normalize_file_name = normalize_file_name.replace(f'{INDICATOR_FIELD}-',
                                                                  f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-')
            # Handle case where "*hello-world.yml"
            else:
                normalize_file_name = f'{INCIDENT_FIELD}-{INDICATOR_FIELD}-{normalize_file_name}'

        return normalize_file_name
