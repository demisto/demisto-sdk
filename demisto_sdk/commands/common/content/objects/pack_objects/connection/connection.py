from typing import Union

from demisto_sdk.commands.common.constants import CANVAS
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from wcmatch.pathlib import Path


class Connection(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, CANVAS)
        self.base = base

    def validate(self):
        return True
