import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_indicator_type_object,
)
from demisto_sdk.commands.validate.validators.RP_validators.RP101_expiration_field_is_numeric import (
    ExpirationFieldIsNumericValidator,
)
from demisto_sdk.commands.validate.validators.RP_validators.RP102_details_field_equals_id import (
    DetailsFieldEqualsIdValidator,
)
from demisto_sdk.commands.validate.validators.RP_validators.RP103_is_valid_indicator_type_id import (
    IsValidIndicatorTypeId,
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
def test_ExpirationFieldIsNumericValidator_obtain_invalid_content_items(
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
    results = ExpirationFieldIsNumericValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_DetailsFieldEqualsIdValidator_obtain_invalid_content_items():
    """
    Given
        - two indicator_type objects:
            - One indicator_type with id equals details.
            - One indicator_type with id not equals details.
    When
        - Calling the DetailsFieldEqualsIdValidator is valid function.
    Then
        - Make sure the right amount of failures return. Should fail object two.
    """
    content_items = [
        create_indicator_type_object(["details", "id"], ["test", "test"]),
        create_indicator_type_object(["details", "id"], ["test", "test-not-equal"]),
    ]
    expected_msgs = [
        "id and details fields are not equal. id=test-not-equal, details=test"
    ]
    results = DetailsFieldEqualsIdValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == 1
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_ValidIndicatorTypeId():
    """
    Given
    content_items iterables.
        - Case 1: One indicator_type with letters string
        - Case 2: One indicator_type with letters string with ampersands
        - Case 3: One indicator_type with letters string with whitespaces
        - Case 4: One indicator_type with letters string with underscores
        - Case 5: One indicator_type with letters string with numbers
    When
    - Calling the IsValidIndicatorTypeId obtain_invalid_content_items function.
    Then
        - Make sure no errors will return.
    """

    content_items = [
        create_indicator_type_object(["id"], ["teststring"]),
        create_indicator_type_object(["id"], ["test&string&with&ampersands&"]),
        create_indicator_type_object(["id"], ["test string with whitespaces"]),
        create_indicator_type_object(["id"], ["test_string_with_underscores"]),
        create_indicator_type_object(["id"], ["test0string1with2numbers3"]),
    ]
    expected_number_of_failures = 0
    expected_msgs = []
    results = IsValidIndicatorTypeId().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_InValidIndicatorTypeId():
    """
    Given
    content_items iterables.
        - Case 1: One indicator_type with invalid special characters.
        - Case 2: One indicator_type with invalid slashes
    When
    - Calling the IsValidIndicatorTypeId obtain_invalid_content_items function.
    Then
        - Make sure it will return 2 errors with the appropriate message.
    """

    content_items = [
        create_indicator_type_object(["id"], ["string_with_special_characters_*#$"]),
        create_indicator_type_object(["id"], ["string_with_slash_/"]),
    ]
    expected_number_of_failures = 2
    expected_msg = (
        "The `id` field must consist of alphanumeric characters (A-Z, a-z, 0-9), whitespaces ( ), "
        "underscores (_), and ampersands (&) only."
    )

    results = IsValidIndicatorTypeId().obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    for result in results:
        assert result.message == expected_msg
