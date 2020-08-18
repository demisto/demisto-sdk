from typing import Union

from demisto_sdk.commands.common.constants import CLASSIFIER, MAPPER
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from wcmatch.pathlib import Path


class Classifier(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, CLASSIFIER)


class OldClassifier(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, CLASSIFIER)


class ClassifierMapper(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, MAPPER)
