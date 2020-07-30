from abc import ABC
from typing import Union

from wcmatch.pathlib import Path

from ...abstract_objects import YAMLUnfiedObject
from demisto_sdk.commands.common.constants import FileType, SCRIPT


class Script(YAMLUnfiedObject, ABC):
    def __init__(self, path: Union[Path, str]) -> Path:
        super().__init__(path, FileType.SCRIPT, SCRIPT)

    @property
    def script(self) -> dict:
        return self.to_dict()

    @property
    def docker_image_4_5(self) -> str:
        return self.script.get('dockerimage45')
