import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.TR_validators.TR100_is_silent_trigger import (
    IsSilentTriggerValidator,
)
from demisto_sdk.commands.validate.validators.TR_validators.TR101_standardized_fields import (
    TriggerStandardizedFieldsValidator,
)


@pytest.mark.parametrize(
    "name, is_silent, result_len, file_name",
    [
        ("test", False, 0, "test"),
        (
            "silent-test",
            True,
            0,
            "silent-test",
        ),
        (
            "test",
            True,
            1,
            "silent-test",
        ),
        (
            "silent-test",
            False,
            1,
            "silent-test",
        ),
        (
            "silent-test",
            False,
            1,
            "test",
        ),
        (
            "test",
            True,
            1,
            "test",
        ),
    ],
)
def test_IsSilentTriggerValidator(name, is_silent, result_len, file_name):
    """
    Given:
        case 1: is_silent = False, and trigger_name/file_name do not contain silent prefix.
        case 2: is_silent = True, and trigger_name/file_name contain silent prefix.
        case 3: is_silent = True, trigger_name contain and file_name do not contain silent prefix.
        case 4: is_silent = False, and trigger_name/file_name contain silent prefix.
        case 5: is_silent = False, trigger_name contain and file_name do not contain silent prefix.
        case 6: is_silent = True, and trigger_name/file_name do not contain silent prefix.

    When:
    - calling IsSilentPlaybookValidator.obtain_invalid_content_items.

    Then:
    - case 1: Passes. Non-silent trigger with no "silent-" prefix in trigger_name or file_name.
    - case 2: Passes. Silent trigger correctly configured with "silent-" in trigger_name and file_name.
    - case 3: Fails. Silent trigger must have "silent-" in both trigger_name and file_name if it appears in one of them.
    - case 4: Fails. Non-silent trigger should not have "silent-" in trigger_name or file_name.
    - case 5: Fails. Non-silent trigger should not have "silent-" in trigger_name without matching file_name.
    - case 6: Fails. Silent trigger must have "silent-" in both trigger_name and file_name.
    """

    trigger = create_trigger_object(file_name=file_name)
    trigger.data["trigger_name"] = name
    trigger.is_silent = is_silent

    invalid_content_items = IsSilentTriggerValidator().obtain_invalid_content_items(
        [trigger]
    )
    assert result_len == len(invalid_content_items)


class TestTriggerStandardizedFieldsValidator:
    def test_valid_trigger_with_standard_fields(self):
        """Test that trigger with standard 'id' and 'name' fields passes validation."""
        trigger = create_trigger_object()
        trigger.data.update({"id": "test-trigger-id", "name": "Test Trigger Name"})

        validator = TriggerStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([trigger])

        assert len(results) == 0

    def test_invalid_trigger_with_old_id_field_only(self):
        """Test that trigger with only 'trigger_id' fails validation."""
        trigger = create_trigger_object()
        trigger.data.update(
            {"trigger_id": "old-trigger-id", "name": "Test Trigger Name"}
        )

        validator = TriggerStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([trigger])

        assert len(results) == 1
        assert results[0].validator.error_code == "TR101"

    def test_invalid_trigger_with_old_name_field_only(self):
        """Test that trigger with only 'trigger_name' fails validation."""
        trigger = create_trigger_object()
        trigger.data.update(
            {"id": "test-trigger-id", "trigger_name": "Old Trigger Name"}
        )

        validator = TriggerStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([trigger])

        assert len(results) == 1
        assert results[0].validator.error_code == "TR101"

    def test_valid_trigger_with_both_fields(self):
        """Test that trigger with both old and new fields passes validation."""
        trigger = create_trigger_object()
        trigger.data.update(
            {
                "id": "test-trigger-id",
                "trigger_id": "old-trigger-id",  # Backward compatibility
                "name": "Test Trigger Name",
                "trigger_name": "Old Trigger Name",  # Backward compatibility
            }
        )

        validator = TriggerStandardizedFieldsValidator()
        results = validator.obtain_invalid_content_items([trigger])

        assert len(results) == 0
