import pytest

from demisto_sdk.commands.common.constants import CLASSIFICATION_TYPE
from demisto_sdk.commands.validate.tests.test_tools import create_classifier_object
from demisto_sdk.commands.validate.validators.CL_validators.CL100_is_valid_classifier_type import (
    IsValidClassifierTypeValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_classifier_object(),
                create_classifier_object(["type"], [""]),
                create_classifier_object(["type"], ["test"]),
            ],
            2,
            [
                f"Classifiers type must be {CLASSIFICATION_TYPE}.",
                f"Classifiers type must be {CLASSIFICATION_TYPE}.",
            ],
        ),
    ],
)
def test_IsValidClassifierTypeValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    3 Classifiers:
        - One valid classifier.
        - One invalid classifier with an empty type field.
        - One invalid classifier with a type field != classification.
    When
    - Calling the IsValidClassifierTypeValidator is valid function.
    Then
        - Make sure the right amount of failures return and that the right message is returned.
    """
    results = IsValidClassifierTypeValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )
