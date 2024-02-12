import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_indicator_type_object,
)
from demisto_sdk.commands.validate.validators.RP_validators.RP101_expiration_field_is_numeric import (
    ExpirationFieldIsNumericValidator,
)


@pytest.mark.parametrize(
    "expected_number_of_failures, content_items, expected_msgs",
    [
        (0, [create_indicator_type_object()], []),
        (0, [create_indicator_type_object(["expiration"], [0])], []),
        (
            2,
            [
                create_indicator_type_object(["expiration"], [0]),
                create_indicator_type_object(["expiration"], [-1]),
                create_indicator_type_object(["expiration"], ["1"]),
            ],
            [
                "The 'expiration' field should have a non-negative integer value, current is: -1 of type <class 'int'>.",
                "The 'expiration' field should have a non-negative integer value, current is: 1 of type <class 'str'>.",
            ],
        ),
    ],
)
def test_ExpirationFieldIsNumericValidator_is_valid(
    content_items, expected_number_of_failures, expected_msgs
):
    """
    Given
    content_items iterables.
        - Case 1: One indicator_type with expiration = 43200.
        - Case 2: One indicator_type with expiration = 0.
        - Case 3: Three indicator_type objects:
            - One indicator_type with expiration = 0.
            - One indicator_type with expiration = -1.
            - One indicator_type with expiration = '1' (string).
    When
    - Calling the ExpirationFieldIsNumericValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Shouldn't fail anything.
        - Case 2: Shouldn't fail anything.
        - Case 3: Should fail object two and three.
    """
    results = ExpirationFieldIsNumericValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )
