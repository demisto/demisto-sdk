from copy import deepcopy
from typing import List, Tuple, Optional, Union
import pandas as pd
from tabulate import tabulate
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.content.content.objects.abstract_objects import (
    YAMLContentObject, YAMLUnfiedObject, JSONContentObject, TextObject)
from demisto_sdk.commands.common.logger import Colors

ContentObject = Union[YAMLUnfiedObject, YAMLContentObject, JSONContentObject, TextObject]


class ObjectReport:
    def __init__(self, content_object: ContentObject, content_test: bool = False, content_packs: bool = False,
                 content_new: bool = False):
        self._content_object_src = content_object.path
        self._content_packs = content_packs
        self._content_test = content_test
        self._content_new = content_new

    def to_dict(self):
        return {
            "source": self._content_object_src,
            "packs": self._content_packs,
            "test": self._content_test,
            "new": self._content_new
        }

    def set_content_new(self):
        self._content_new = True

    def set_content_packs(self):
        self._content_packs = True

    def set_content_test(self):
        self._content_test = True


class ArtifactsReport:
    def __init__(self, header: str):
        self._header = header
        self._content_objects: List[dict] = []

    def append(self, object_report: ObjectReport):
        self._content_objects.append(object_report.to_dict())

    def __iadd__(self, object_report: ObjectReport):
        self._content_objects.append(object_report.to_dict())

        return self

    def to_str(self, src_relative_to: Path = None):
        objects = deepcopy(self._content_objects)
        if src_relative_to:
            for item in objects:
                item['source'] = str(item['source'].relative_to(src_relative_to))
        table = pd.DataFrame(data=objects,
                             columns=["source", "packs", "new", "test"])

        return Colors.Fg.cyan + f'\n{self._header}\n' + Colors.reset + tabulate(table, headers='keys', tablefmt='psql')
