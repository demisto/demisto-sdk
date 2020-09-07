from typing import Union

from demisto_sdk.commands.common.constants import PLAYBOOK
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from wcmatch.pathlib import Path


class Playbook(YAMLContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, PLAYBOOK)
