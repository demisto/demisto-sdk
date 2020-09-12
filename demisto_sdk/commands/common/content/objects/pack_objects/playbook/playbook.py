from typing import Union

from demisto_sdk.commands.common.constants import PLAYBOOK
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import YamlFile
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.yaml_pack_mixins import \
    YamlPackMixin, YamlPackDumpMixin
from wcmatch.pathlib import Path


class Playbook(YamlFile, YamlPackMixin, YamlPackDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super(YamlFile).__init__(path=path, prefix=PLAYBOOK)
