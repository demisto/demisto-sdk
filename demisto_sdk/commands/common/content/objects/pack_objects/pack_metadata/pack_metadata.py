from typing import Union

from demisto_sdk.commands.common.content.objects.abstract_objects import \
    JSONObject
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from wcmatch.pathlib import Path


class PackMetaData(JSONObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path)
