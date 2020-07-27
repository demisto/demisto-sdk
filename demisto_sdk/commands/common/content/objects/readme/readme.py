from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstart_objects.abstract_data_objects.text_object import TextObject


class Readme(TextObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path)
