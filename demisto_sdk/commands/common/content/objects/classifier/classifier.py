from typing import Union

from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.objects.abstart_objects.json_content_object import JSONContentObject
from demisto_sdk.commands.common.constants import CLASSIFIER


class Classifier(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, CLASSIFIER)
