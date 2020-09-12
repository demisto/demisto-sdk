from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.base_objects.bytes_file import BytesFile
from demisto_sdk.commands.common.content.objects.base_objects.dump_file_mixin import FileDumpMixin


class PackIgnore(BytesFile, FileDumpMixin):
    def __init__(self, path: Union[Path, str]):
        super(BytesFile).__init__(path=path)
