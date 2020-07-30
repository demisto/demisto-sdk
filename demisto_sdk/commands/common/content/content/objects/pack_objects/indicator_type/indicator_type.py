from typing import Union

from wcmatch.pathlib import Path

from ...abstract_objects import JSONContentObject
from demisto_sdk.commands.common.constants import INDICATOR_TYPE, OLD_INDICATOR_TYPE


class IndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INDICATOR_TYPE)


class OldIndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, OLD_INDICATOR_TYPE)

    def _normalized_file_name(self):
        file_normalized_name = self._path.name
        if self._path.suffix:
            file_normalized_name = ".".join(file_normalized_name.split('.')[:-1])
        if self._prefix and not file_normalized_name.startswith(f'{self._prefix}'):
            file_normalized_name = f'{self._prefix}-{file_normalized_name}'

        return f'{file_normalized_name}{self._path.suffix}'
