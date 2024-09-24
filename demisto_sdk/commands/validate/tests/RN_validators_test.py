import pytest

from demisto_sdk.commands.validate.tests.test_tools import (
    create_incoming_mapper_object,
    create_integration_object,
    create_old_file_pointers,
    create_pack_object,
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN103_is_release_notes_filled_out import (
    IsReleaseNotesFilledOutValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN105_multiple_rns_added import (
    MultipleRNsAddedValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN108_is_rn_added_to_new_pack import (
    IsRNAddedToNewPackValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN112_is_bc_rn_exist import (
    IsBCRNExistValidator,
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


def test_release_note_header_validator_valid():
    """
    Given:
    - content_items.
        pack_metadata:
            1. valid release note headers.
            2. Trigger (edge case).
            3. Mapper (edge case).
    When:
    - Calling the ReleaseNoteHeaderValidator is_valid function.

    Then:
    - Make sure the validation passes.
    """
    pack = create_pack_object(
        paths=["version"],
        values=["2.0.5"],
        release_note_content="#### Integrations\n"
        "##### TestIntegration\n"
        "This is an exemple\n",
    )
    integrations = [
        create_integration_object(["name"], ["TestIntegration"]),
    ]
    pack.content_items.integration.extend(integrations)
    results = ReleaseNoteHeaderValidator().obtain_invalid_content_items(
        content_items=[pack]
    )
    assert len(results) == 0


def test_release_note_header_validator_edge_cases_valid():
    """
    Given:
    - content_items.
        pack_metadata:
            - Trigger (edge case).
            - Mapper (edge case).
    When:
    - Calling the ReleaseNoteHeaderValidator is_valid function.

    Then:
    - Make sure the validation passes.
    """
    pack = create_pack_object(
        paths=["version"],
        values=["2.0.5"],
        release_note_content="#### Triggers Recommendations\n"
        "##### NGFW Scanning Alerts\n"
        "- This trigger is responsible for handling alerts.\n"
        "#### Mappers\n"
        "##### GitHub Mapper\n"
        "- Added an incoming Mapper (Available from Cortex XSOAR 6.5.0)\n ",
    )
    pack.content_items.trigger.extend([create_trigger_object()])
    pack.content_items.mapper.extend([create_incoming_mapper_object()])
    results = ReleaseNoteHeaderValidator().obtain_invalid_content_items(
        content_items=[pack]
    )
    assert len(results) == 0


def test_release_note_header_validator_invalid():
    """
    Given:
    - content_items.
        pack_metadata: pack with invalid release note headers.

    When:
    - Calling the ReleaseNoteHeaderValidator is_valid function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
    """
    expected_error = "The following release note headers are invalid:\nContent types: InvalidHeader\n\nContent items: Integrations: Not exist content item\n\n"
    pack = create_pack_object(
        paths=["version"],
        values=["2.0.5"],
        release_note_content="#### Integrations\n"
        "##### Not exist content item\n"
        "This is an example\n"
        "#### InvalidHeader\n"
        "##### playbook A\n",
    )
    integrations = [
        create_integration_object(),
    ]
    pack.content_items.integration.extend(integrations)
    results = ReleaseNoteHeaderValidator().obtain_invalid_content_items(
        content_items=[pack]
    )
    assert expected_error == results[0].message


def test_MultipleRNsAddedValidator_obtain_invalid_content_items():
    """
    Given:
    - content_items.
        - Case 1: A pack with 1 new RN.
        - Case 2: A Pack with 1 new RN with BC json file.
        - Case 3: A pack with 2 new RNs.

    When:
    - Calling the MultipleRNsAddedValidator is_valid function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Shouldn't fail anything.
        - Case 2: Shouldn't fail anything.
        - Case 3: Should fail.
    """
    expected_error = "The pack contains more than one new release note, please make sure the pack contains at most one release note."
    pack = create_pack_object(
        paths=["version"],
        values=["2.0.5"],
        release_note_content="The new RN",
    )
    old_pack = create_pack_object(
        paths=["version"],
        values=["2.0.4"],
        release_note_content="The old RN",
    )
    create_old_file_pointers([pack], [old_pack])
    validator = MultipleRNsAddedValidator()
    assert not validator.obtain_invalid_content_items(content_items=[pack])
    pack.release_note.all_rns.append("2.0.5.json")
    assert not validator.obtain_invalid_content_items(content_items=[pack])
    pack.release_note.all_rns.append("2.0.6.md")
    results = validator.obtain_invalid_content_items(content_items=[pack])
    assert expected_error == results[0].message


def test_IsBCRNExistValidator_obtain_invalid_content_items():
    """
    Given:
    - 4 Pack content items with rns.
        - Case 1: A pack with 1 new RN without BC entry.
        - Case 2: A pack with 1 new RN with a BC entry, but no json bc file.
        - Case 3: A pack with 1 new RN with a BC entry, and a json bc file without breakingChanges entry.
        - Case 4: A pack with 1 new RN with a BC entry, and a json bc file with breakingChanges entry.

    When:
    - Calling the IsBCRNExistValidator is_valid function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Shouldn't fail.
        - Case 2: Should fail.
        - Case 3: Should fail.
        - Case 1: Shouldn't fail.
    """
    content_items = [
        create_pack_object(
            paths=["version"],
            values=["2.0.5"],
            release_note_content="some change",
        ),
        create_pack_object(
            paths=["version"],
            values=["2.0.5"],
            release_note_content="breaking change",
        ),
        create_pack_object(
            paths=["version"],
            values=["2.0.5"],
            release_note_content="breaking change",
            bc_release_note_content=[{"test": "no breaking change content"}],
        ),
        create_pack_object(
            paths=["version"],
            values=["2.0.5"],
            release_note_content="breaking change",
            bc_release_note_content=[
                {"breakingChanges": "some breaking change content"}
            ],
        ),
    ]
    results = IsBCRNExistValidator().obtain_invalid_content_items(
        content_items=content_items
    )
    expected_msgs = [
        f"The release notes contain information about breaking changes but missing a breaking change file, make sure to add one as {str(content_items[1].release_note.file_path).replace('.md', '.json')} and that the file contains the 'breakingChanges' entry.",
        f"The release notes contain information about breaking changes but missing a breaking change file, make sure to add one as {str(content_items[2].release_note.file_path).replace('.md', '.json')} and that the file contains the 'breakingChanges' entry.",
    ]

    assert len(results) == 2
    assert all(
        [
            result.message == expected_msg
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )
