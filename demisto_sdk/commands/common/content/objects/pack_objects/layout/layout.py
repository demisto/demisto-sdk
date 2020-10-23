from typing import Union

from demisto_sdk.commands.common.constants import LAYOUT, LAYOUTS_CONTAINER
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


class Layout(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, LAYOUT)


class LayoutsContainer(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, LAYOUTS_CONTAINER)
