import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_integration_object,
    create_script_object,
)
from demisto_sdk.commands.validate.validators.BC_validators.BC100_breaking_backwards_subtype import (
    BreakingBackwardsSubtypeValidator,
)


@pytest.mark.parametrize(
    "content_items, old_content_items, expected_number_of_failures",
    [
        ([create_integration_object(key_path="script.subtype", new_value="python2"), create_integration_object()],
         [create_integration_object(), create_integration_object()], 1),
        ([create_integration_object(key_path="script.subtype", new_value="python2"), create_script_object()],
         [create_integration_object(), create_script_object()], 1),
        ([create_integration_object(key_path="script.subtype", new_value="python2"), create_script_object(key_path="subtype", new_value="python2")],
         [create_integration_object(), create_script_object()], 2),
        ([create_integration_object(), create_script_object()],
         [create_integration_object(), create_script_object()], 0),
    ],
)
def test_BreakingBackwardsSubtypeValidator(content_items, old_content_items, expected_number_of_failures):
    """
    Given
    content_items and old_content_items iterables.
        - Case 1: content_items with 2 integrations where the first one has its subtype altered, and two integration with no changes in old_content_items.
        - Case 2: content_items with 1 integration where the first one has its subtype altered and one script with no subtype altered, and old_content_items with one script and integration with no changes.
        - Case 3: content_items with 1 integration where the first one has its subtype altered and 1 script where that has its subtype altered, and old_content_items with one script and integration with no changes.
        - Case 4: content_items and old_content_items with 1 integration and 1 script both with no changes
    When
    - Calling the BreakingBackwardsSubtypeValidator is valid function.
    Then
        - Make sure the right amount of failures return.
        - Case 1: Should fail 1 integration.
        - Case 2: Should fail 1 integration.
        - Case 3: Should fail both the integration and the script
        - Case 4: Shouldn't fail any content item.
    """
    assert len(BreakingBackwardsSubtypeValidator().is_valid(content_items, old_content_items)) == expected_number_of_failures
