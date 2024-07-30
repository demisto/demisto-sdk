import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN103_is_release_notes_filled_out import (
    IsReleaseNotesFilledOutValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN108_is_rn_added_to_new_pack import (
    IsRNAddedToNewPackValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_pack_object(
                    paths=["version"],
                    values=["2.0.5"],
                    release_note_content="This is a valid rn.",
                ),  # valid release_note
                create_pack_object(
                    paths=["version"],
                    values=["2.0.5"],
                    release_note_content="",
                ),  # empty release_note
                create_pack_object(
                    paths=["version"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%UPDATE_RN%%",
                ),  # shouldn't pass as it has an invalid release note
                create_pack_object(
                    paths=["version"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%XSIAM_VERSION%%",
                ),  # shouldn't pass as it has an invalid release note
                create_pack_object(
                    paths=["version"],
                    values=["1.0.0"],
                ),
            ],
            3,
            [
                "Please complete the release notes and ensure all placeholders are filled in."
                "For common troubleshooting steps, please review the documentation found here: "
                "https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips"
            ],
        ),
    ],
)
def test_release_note_filled_out_validator(
    content_items,
    expected_number_of_failures,
    expected_msgs,
):
    """
    Given:
    - content_items.
        - Case 1: Five pack_metadatas:
            - 1 pack with valid release note.
            - 1 pack with an invalid empty release note.
            - 1 pack with invalid release note.
            - 1 pack with invalid release note.
            - 1 pack without any release notes.

    When:
    - Calling the IsReleaseNotesFilledOutValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
    """

    results = IsReleaseNotesFilledOutValidator().obtain_invalid_content_items(
        content_items
    )
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_IsRNAddedToNewPackValidator_obtain_invalid_content_items():
    """
    Given:
    - content_items.
        - Case 1: A new pack metadata without RNs.
        - Case 2: A new pack metadata with RN.

    When:
    - Calling the IsRNAddedToNewPackValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
        - Case 1: Should pass.
        - Case 2: Should fail.
    """
    valid_content_items = [create_pack_object()]
    validator = IsRNAddedToNewPackValidator()
    assert not validator.obtain_invalid_content_items(valid_content_items)
    invalid_content_items = [
        create_pack_object(
            paths=["version"], values=["1.0.1"], release_note_content="should fail"
        )
    ]
    invalid_content_items[0].current_version = "1.0.0"
    invalid_results = validator.obtain_invalid_content_items(invalid_content_items)
    assert len(invalid_results) == 1
    assert (
        invalid_results[0].message
        == "The Pack is a new pack and contains release notes, please remove all release notes."
    )
