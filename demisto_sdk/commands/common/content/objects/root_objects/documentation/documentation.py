from typing import Union

from demisto_sdk.commands.common.constants import DOCUMENTATION
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.base_objects.dump_file_mixin import FileDumpMixin
from demisto_sdk.commands.common.content.objects.base_objects.json_file import JsonFile


class Documentation(JsonFile, FileDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super(JsonFile).__init__(path=path, prefix=DOCUMENTATION)
