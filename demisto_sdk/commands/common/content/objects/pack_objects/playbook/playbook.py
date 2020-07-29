from abc import ABC
from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstract_objects.abstract_content_files.yaml_content_object import YAMLConentObject
from demisto_sdk.commands.common.constants import PLAYBOOK


class Playbook(YAMLConentObject, ABC):
    def __init__(self, path: Union[Path, str]) -> Path:
        super().__init__(path, PLAYBOOK)
