from typing import Union

from demisto_sdk.commands.common.constants import SCRIPT
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import YamlFile
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.yaml_pack_unify_mixins import \
    YamlPackUnifyMixin, YamlPackUnifyDumpMixin
from wcmatch.pathlib import Path


class Script(YamlFile, YamlPackUnifyMixin, YamlPackUnifyDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super(YamlFile).__init__(path=path, prefix=SCRIPT)

    @property
    def script(self) -> dict:
        """Script item in object dict"""
        return self.__dict__()
