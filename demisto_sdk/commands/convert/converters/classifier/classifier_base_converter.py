import os
from abc import abstractmethod
from typing import Optional, Set

from demisto_sdk.commands.common.constants import FileType
from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import (
    Classifier,
)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.tools import get_yaml
from demisto_sdk.commands.convert.converters.base_converter import BaseConverter


class ClassifierBaseConverter(BaseConverter):
    CLASSIFIER_UP_TO_5_9_9_SCHEMA_PATH = os.path.normpath(
        os.path.join(
            __file__,
            "..",
            "..",
            "..",
            "..",
            "common/schemas/",
            f"{FileType.OLD_CLASSIFIER.value}.yml",
        )
    )

    CLASSIFIER_6_0_0_SCHEMA_PATH = os.path.normpath(
        os.path.join(
            __file__,
            "..",
            "..",
            "..",
            "..",
            "common/schemas/",
            f"{FileType.CLASSIFIER.value}.yml",
        )
    )

    INTERSECTION_FIELDS_TO_EXCLUDE = {"fromVersion", "toVersion", "id"}

    def __init__(self, pack: Pack):
        super().__init__()
        self.pack = pack

    @abstractmethod
    def convert_dir(self) -> int:
        pass

    def get_classifiers_schema_intersection_fields(self) -> Set[str]:
        """
        Receives schema path of two classifiers, returns the fields intersecting inside mapping field value.

        Returns:
            (Set[str]): Set containing all intersecting fields inside mapping field value.
        """
        first_schema_data: dict = get_yaml(self.CLASSIFIER_UP_TO_5_9_9_SCHEMA_PATH).get(
            "mapping", dict()
        )
        second_schema_data: dict = get_yaml(self.CLASSIFIER_6_0_0_SCHEMA_PATH).get(
            "mapping", dict()
        )
        intersecting_fields = first_schema_data.keys() & second_schema_data.keys()
        return {
            field
            for field in intersecting_fields
            if field not in self.INTERSECTION_FIELDS_TO_EXCLUDE
        }

    @staticmethod
    def extract_classifier_name(classifier: Classifier) -> Optional[str]:
        """
        Receives classifier object, returns the name given to the classifier object, if follows the expected file
        naming conventions.
        Args:
            classifier (Classifier): The classifier object.

        Returns:
            (Optional[str]):
            - (str): If file name followed the file naming convention.
            - (None): If file had unexpected naming.
        """
        file_name = os.path.basename(classifier.path)
        if not file_name.startswith("classifier-") or not file_name.endswith(
            "_5_9_9.json"
        ):
            return None
        classifier_base_name = file_name.split("-")[1].split("_5_9_9")[0]
        return classifier_base_name
