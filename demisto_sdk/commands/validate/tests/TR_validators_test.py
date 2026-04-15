import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.TR_validators.TR101_is_valid_trigger_id import (
    IsValidTriggerIdValidator,
)
from demisto_sdk.commands.validate.validators.TR_validators.TR100_is_silent_trigger import (
    IsSilentTriggerValidator,
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


@pytest.mark.parametrize(
    "trigger_id, expected_result_len",
    [
        ("9ba5cc715622f50eddd58ab5c413f58b", 0),
        ("73545719a1bdeba6ba91f6a16044c021", 0),
        ("ABCDEF0123456789abcdef0123456789", 0),
        ("aabbcc", 0),
        ("9ba5cc71-5622-f50e-ddd5-8ab5c413f58b", 1),
        ("9ba5cc71.5622.f50e", 1),
        ("my-trigger-name", 1),
        ("xyz123", 1),
        ("trigger id with spaces", 1),
        ("", 1),
    ],
)
def test_IsValidTriggerIdValidator(trigger_id, expected_result_len):
    """
    Given:
        case 1: A valid hex trigger_id.
        case 2: Another valid hex trigger_id.
        case 3: A valid hex trigger_id with mixed case.
        case 4: A short valid hex trigger_id.
        case 5: A trigger_id with dashes (UUID format).
        case 6: A trigger_id with dots.
        case 7: A trigger_id with non-hex characters and dashes.
        case 8: A trigger_id with non-hex characters (x, y, z).
        case 9: A trigger_id with spaces.
        case 10: An empty trigger_id.

    When:
    - calling IsValidTriggerIdValidator.obtain_invalid_content_items.

    Then:
    - cases 1-4: Pass. Valid hex string trigger_ids.
    - cases 5-10: Fail. Invalid trigger_ids containing special characters or non-hex characters.
    """
    trigger = create_trigger_object(
        paths=["trigger_id"], values=[trigger_id]
    )

    invalid_content_items = IsValidTriggerIdValidator().obtain_invalid_content_items(
        [trigger]
    )
    assert expected_result_len == len(invalid_content_items)
