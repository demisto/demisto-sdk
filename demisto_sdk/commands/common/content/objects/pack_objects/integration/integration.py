from typing import Optional, Union

from demisto_sdk.commands.common.constants import INTEGRATION
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import YamlFile
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.yaml_pack_unify_mixins import \
    YamlPackUnifyMixin, YamlPackUnifyDumpMixin
from wcmatch.pathlib import Path


class Integration(YamlFile, YamlPackUnifyMixin, YamlPackUnifyDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path=path, prefix=INTEGRATION)

    @property
    def script(self) -> dict:
        """Script item in object dict"""
        return self.get('script', {})

    @property
    def png_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_image.png"]
        return next(self._path.parent.glob(patterns=patterns), None)

    @property
    def description_path(self) -> Optional[Path]:
        patterns = [f"{self.path.stem}_description.md"]
        return next(self._path.parent.glob(patterns=patterns), None)
