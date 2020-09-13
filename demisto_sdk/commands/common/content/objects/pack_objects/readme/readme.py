from typing import Union

from demisto_sdk.commands.common.content.objects.base_objects.bytes_file import \
    BytesFile
from demisto_sdk.commands.common.content.objects.base_objects.common import \
    FileDumpMixin
from wcmatch.pathlib import Path


class Readme(BytesFile, FileDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path=path)
