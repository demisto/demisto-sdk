from typing import Union

from demisto_sdk.commands.common.constants import SCRIPT, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnfiedObject
from wcmatch.pathlib import Path


class Script(YAMLContentUnfiedObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.SCRIPT, SCRIPT)

    @property
    def script(self) -> dict:
        return self.to_dict()
