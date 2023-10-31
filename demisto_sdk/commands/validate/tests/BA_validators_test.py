import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_classifier_object,
    create_dashboard_object,
    create_incident_type_object,
    create_integration_object,
    create_wizard_object,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures",
    [
        (
            [
                create_integration_object(
                    key_path="commonfields.id", new_value="changedName"
                ),
                create_integration_object(),
            ],
            1,
        ),
        (
            [
                create_classifier_object(
                    key_path="id", new_value="changedName"
                ),
                create_classifier_object(
                    key_path="id", new_value="Github Classifier"
                ),
            ],
            1,
        ),
        (
            [
                create_dashboard_object(),
            ],
            0,
        ),
        (
            [
                create_incident_type_object(),
            ],
            0,
        ),
        (
            [
                create_wizard_object(),
            ],
            0,
        ),
        (
            [
                create_wizard_object({"id": "should_fail"}),
            ],
            1,
        ),
    ],
)
def test_IDNameValidator_is_valid(content_items, expected_number_of_failures):
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
    assert (
        len(IDNameValidator().is_valid(content_items, None))
        == expected_number_of_failures
    )

@pytest.mark.parametrize(
    "content_item, expected_name",
    [
        (
            create_wizard_object({"id": "should_fix"}), "should_fix",
        ),
    ],
)
def test_IDNameValidator_fix(content_item, expected_name):
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
    IDNameValidator().fix(content_item, None)
    assert content_item.name == expected_name
