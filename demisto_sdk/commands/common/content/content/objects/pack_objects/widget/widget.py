from typing import Union

from wcmatch.pathlib import Path


from demisto_sdk.commands.common.constants import WIDGET
from ...abstract_objects import JSONContentObject


class Widget(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, WIDGET)
