from abc import ABC
from typing import Union

from wcmatch.pathlib import Path

from ...abstract_objects import YAMLUnfiedObject
from demisto_sdk.commands.common.constants import FileType, INTEGRATION


class Integration(YAMLUnfiedObject, ABC):
    def __init__(self, path: Union[Path, str]) -> Path:
        super().__init__(path, FileType.INTEGRATION, INTEGRATION)

    @property
    def script(self) -> dict:
        return self.get('script', {})


