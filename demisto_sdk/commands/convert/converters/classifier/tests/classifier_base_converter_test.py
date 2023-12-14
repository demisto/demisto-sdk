import os
from typing import Optional

import pytest

from demisto_sdk.commands.common.content.objects.pack_objects.classifier.classifier import (
    Classifier,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.convert.converters.classifier.classifier_base_converter import (
    ClassifierBaseConverter,
)


class TestLayoutBaseConverter:
    def test_get_classifiers_schema_intersection_fields(self, tmpdir):
        """
        Given:
        - Two schemas of classifiers (classifier 5_9_9 and below, classifier 6_0_0 and above schemas

        When:
        - Wanting to retrieve all intersecting fields between schemas that are not excluded.

        Then:
        - Ensure expected intersecting fields are returned.

        """
        classifier_converter = ClassifierBaseConverter(tmpdir)
        result = classifier_converter.get_classifiers_schema_intersection_fields()
        assert all(
            field in result
            for field in (
                "custom",
                "defaultIncidentType",
                "feed",
                "incidentSamples",
                "indicatorSamples",
                "isDefault",
                "keyTypeMap",
                "modified",
                "propagationLabels",
                "sortValues",
                "transformer",
                "unclassifiedCases",
                "version",
            )
        )

    EXTRACT_CLASSIFIER_NAME_INPUTS = [
        ("classifier-Cymulate_5_9_9", "Cymulate"),
        ("classifier-Cymulate", None),
    ]

    @pytest.mark.parametrize(
        "classifier_name, expected", EXTRACT_CLASSIFIER_NAME_INPUTS
    )
    def test_extract_classifier_name(
        self, classifier_name: str, expected: Optional[str]
    ):
        """
        Given:
        - Old classifier object.

        When:
        - Wanting to retrieve its name from the path.

        Then:
        - Ensure expected name is extracted, if name corresponds to the expected naming format. None if not.

        """
        old_classifier_path = os.path.normpath(
            os.path.join(
                __file__,
                f"{git_path()}/demisto_sdk/commands/convert/converters/"
                f"classifier/tests/test_data/{classifier_name}.json",
            )
        )
        classifier = Classifier(old_classifier_path)
        assert ClassifierBaseConverter.extract_classifier_name(classifier) == expected
