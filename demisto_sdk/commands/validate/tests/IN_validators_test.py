import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN108_is_valid_subtype import (
    ValidSubtypeValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        (
            [
                create_integration_object(key_path="script.subtype", new_value="test"),
                create_integration_object(),
            ],
            1,
        ),
        (
            [
                create_script_object(key_path="subtype", new_value="test"),
                create_script_object(),
            ],
            1,
        ),
        (
            [
                create_script_object(),
                create_integration_object(),
            ],
            0,
        ),
        (
            [
                create_script_object(key_path="subtype", new_value="test"),
                create_integration_object(key_path="script.subtype", new_value="test"),
            ],
            2,
        ),
    ],
)
def test_ValidSubtypeValidator_is_valid(content_items, expected_number_of_failures):
    """
    Given
    content_items iterables.
        - Case 1: content_items with 2 integrations where the first one has subtype different from python2/3 and the second one does.
        - Case 2: content_items with 2 script where the first one has subtype different from python2/3 and the second one does.
        - Case 3: content_items with one script and one integration where both have python3 as subtype.
        - Case 4: content_items with one script and one integration where both dont have python2/python3 as subtype.
    When
    - Calling the ValidSubtypeValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 script.
        - Case 3: Should'nt fail at all.
        - Case 4: Should fail all content items.
    """
    assert (
        len(ValidSubtypeValidator().is_valid(content_items))
        == expected_number_of_failures
    )
