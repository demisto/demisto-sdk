from abc import ABC
from typing import Union

from wcmatch.pathlib import Path

from ...abstract_objects import YAMLContentObject
from demisto_sdk.commands.common.constants import PLAYBOOK


class Playbook(YAMLContentObject, ABC):
    def __init__(self, path: Union[Path, str]) -> Path:
        super().__init__(path, PLAYBOOK)
