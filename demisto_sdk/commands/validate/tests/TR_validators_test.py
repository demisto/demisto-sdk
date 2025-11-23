import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_trigger_object,
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
