from typing import Optional, Union

from demisto_sdk.commands.common.constants import INTEGRATION, FileType
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_unify_content_object import \
    YAMLContentUnifiedObject
from wcmatch.pathlib import Path


class Integration(YAMLContentUnifiedObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, FileType.INTEGRATION, INTEGRATION)

    @property
    def png_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_image.png"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def description_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_description.md"]
        return next(self._path.parent.glob(patterns=patterns), None)
