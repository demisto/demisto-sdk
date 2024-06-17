import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
    create_integration_object,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN103_is_release_notes_filled_out import (
    IsReleaseNotesFilledOutValidator,
)

from demisto_sdk.commands.validate.validators.RN_validators.RN114_validate_release_notes_header import (
    ReleaseNoteHeaderValidator,
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
        - Case 1: Four pack_metadatas:
            - 1 pack with valid release note.
            - 1 pack with an invalid empty release note.
            - 1 pack with invalid release note.
            - 1 pack with invalid release note.

    When:
    - Calling the IsReleaseNotesFilledOutValidator is_valid function.

    Then:
    - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
    """

    results = IsReleaseNotesFilledOutValidator().is_valid(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )


def test_release_note_header_validator_valid():
    """
        Given:
        - content_items.
            pack_metadata: pack with valid release note headers.

        When:
        - Calling the ReleaseNoteHeaderValidator is_valid function.

        Then:
        - Make sure the validation passes.
    """
    pack = create_pack_object(
        paths=["version"],
        values=["2.0.5"],
        release_note_content="#### Integrations\n"
                             "##### TestIntegration1\n"
                             "This is an exemple\n\n"
                             "##### TestIntegration2\n"
                             "This is an exemple too\n   "
    )
    integrations = [
        create_integration_object(
            ["name"], [ "TestIntegration1"]
        ),
        create_integration_object(
             ["name"], ["TestIntegration2"]
        )
    ]
    pack.content_items.integration.extend(integrations)
    results = ReleaseNoteHeaderValidator().is_valid(content_items=[pack])
    assert len(results) == 0


def test_release_note_header_validator_valid():
    """
        Given:
        - content_items.
            pack_metadata: pack with invalid release note headers.

        When:
        - Calling the ReleaseNoteHeaderValidator is_valid function.

        Then:
        - Make sure the right amount of pack metadatas failed, and that the right error message is returned.
    """
    expected_error = ('The invalid header(s) were found.\n'
                      'The content header(s) type are invalid: InvalidHeader\n'
                      'those are the items: playbook A\n'
                      'For common troubleshooting steps, please review the documentation'
                      ' found here: https://xsoar.pan.dev/docs/integrations/changelog#common-troubleshooting-tips')
    pack = create_pack_object(
        paths=["version"],
        values=["2.0.5"],
        release_note_content="#### Integrations\n"
                             "##### TestIntegration1\n"
                             "This is an exemple\n\n"
                             "##### Not exist content item\n"
                             "This is an exemple too\n"
                             "#### InvalidHeader\n"
                             "##### playbook A\n"
    )
    integrations = [
        create_integration_object(
            ["name"], ["TestIntegration1"]
        ),
        create_integration_object(
             ["name"], ["TestIntegration2"]
        )
    ]
    pack.content_items.integration.extend(integrations)
    results = ReleaseNoteHeaderValidator().is_valid(content_items=[pack])
    assert expected_error == results[0].message


