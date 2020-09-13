from typing import Union

from demisto_sdk.commands.common.constants import SCRIPT
from demisto_sdk.commands.common.content.objects.base_objects.yaml_file import \
    YamlFile
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.yaml_pack_mixins import (
    YamlPackReamdeMixin, YamlPackVersionsMixin)
from demisto_sdk.commands.common.content.objects.pack_objects.base_mixins.yaml_pack_unify_mixins import (
    YamlPackUnifyDockerImages, YamlPackUnifyDumpMixin, YamlPackUnifyFilesMixin)
from wcmatch.pathlib import Path


class Script(YamlFile, YamlPackVersionsMixin, YamlPackReamdeMixin, YamlPackUnifyDockerImages, YamlPackUnifyFilesMixin,
             YamlPackUnifyDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path=path, prefix=SCRIPT)
