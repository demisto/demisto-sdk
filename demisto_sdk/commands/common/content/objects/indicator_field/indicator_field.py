from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstart_objects.json_content_object import JSONContentObject
from demisto_sdk.commands.common.constants import INDICATOR_FIELD, INCIDENT_FIELD


class IndicatorField(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INDICATOR_FIELD)

    def _normalized_file_name(self, file_name_suffix: str = ""):
        file_normalized_name = self._path.name
        if self._path.suffix:
            file_normalized_name = ".".join(file_normalized_name.split('.')[:-1])
        if self._prefix and file_normalized_name.startswith(f'{INCIDENT_FIELD}-'):
            file_normalized_name = file_normalized_name.replace(f'{INCIDENT_FIELD}-', f'{INCIDENT_FIELD}-{self._prefix}-')
        else:
            file_normalized_name = f'{INCIDENT_FIELD}-{self._prefix}-{file_normalized_name}'
        if file_name_suffix:
            file_normalized_name = f'{file_normalized_name}-{file_name_suffix}'

        return f'{file_normalized_name}{self._path.suffix}'
