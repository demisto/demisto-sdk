from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import ASSETS_MODELING_RULE, FileType
from demisto_sdk.commands.common.content.objects.pack_objects import ModelingRule
from demisto_sdk.commands.common.tools import generate_xsiam_normalized_name


class AssetsModelingRule(ModelingRule):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.ASSETS_MODELING_RULE, ASSETS_MODELING_RULE)

    def normalize_file_name(self) -> str:
        return generate_xsiam_normalized_name(self._path.name, ASSETS_MODELING_RULE)

    def type(self):
        return FileType.ASSETS_MODELING_RULE
