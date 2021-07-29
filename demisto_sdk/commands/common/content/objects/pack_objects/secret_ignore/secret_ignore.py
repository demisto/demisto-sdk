from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstract_objects import \
    TextObject


class SecretIgnore(TextObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
