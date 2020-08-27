from copy import deepcopy
from typing import List, Union

from demisto_sdk.commands.common.content.objects.pack_objects import (
    JSONContentObject, TextObject, YAMLContentObject, YAMLContentUnifiedObject)
from demisto_sdk.commands.common.logger import Colors
from pandas import DataFrame
from tabulate import tabulate
from wcmatch.pathlib import Path

ContentObject = Union[YAMLContentUnifiedObject, YAMLContentObject, JSONContentObject, TextObject]


class ObjectReport:
    def __init__(self, content_object: ContentObject, content_test: bool = False, content_packs: bool = False,
                 content_new: bool = False, content_all: bool = False):
        """ Content objcet report, Each object has the following include state:
                1. content_test.
                2. content_new.
                3. content_packs.
                4. content_all.

        Args:
            content_object: content object (Integration etc)
            content_test: True if include in content_test.
            content_packs: True if include in content_packs.
            content_new: True if include in content_new.
            content_all: True if include in content_all.
        """
        self._content_object_src = content_object.path
        self._content_packs = content_packs
        self._content_test = content_test
        self._content_new = content_new
        self._content_all = content_all

    def to_dict(self):
        """Class to dict used in order to populate table using paandas"""
        return {
            "source": self._content_object_src,
            "packs": self._content_packs,
            "test": self._content_test,
            "new": self._content_new,
            "all": self._content_all
        }

    def set_content_new(self):
        """Set content_new include state to True"""
        self._content_new = True

    def set_content_packs(self):
        """Set content_packs include state to True"""
        self._content_packs = True

    def set_content_test(self):
        """Set content_test include state to True"""
        self._content_test = True

    def set_content_all(self):
        """Set content_all include state to True"""
        self._content_all = True


class ArtifactsReport:
    def __init__(self, header: str):
        """ Artifact report build from:
                1. Table header.
                2. Object reports entries.

        Args:
            header: Table header.
        """
        self._header = header
        self._content_objects: List[dict] = []

    def append(self, object_report: ObjectReport):
        """Append object report to entries"""
        self._content_objects.append(object_report.to_dict())

    def __iadd__(self, object_report: ObjectReport):
        """Append object report to entries using + operator"""
        self._content_objects.append(object_report.to_dict())

        return self

    def to_str(self, src_relative_to: Path = None):
        """ Create pandas table as pretty string.

        Args:
            src_relative_to: content path to show content object path relative to.

        Returns:
            str: Table with entries which specified include rule for every content object path.
        """
        objects = deepcopy(self._content_objects)
        if src_relative_to:
            for item in objects:
                item['source'] = str(item['source'].relative_to(src_relative_to))
        table = DataFrame(data=objects)

        return Colors.Fg.cyan + f'\n{self._header}\n' + Colors.reset + tabulate(table, headers='keys', tablefmt='psql')
