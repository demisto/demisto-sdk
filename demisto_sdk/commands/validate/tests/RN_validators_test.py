import pytest

from demisto_sdk.commands.common.constants import API_MODULES_PACK, GitStatuses
from demisto_sdk.commands.content_graph.interface import ContentGraphInterface
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.validate.tests.test_tools import (
    create_incoming_mapper_object,
    create_integration_object,
    create_old_file_pointers,
    create_pack_object,
    create_playbook_object,
    create_script_object,
    create_test_playbook_object,
    create_trigger_object,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN103_is_release_notes_filled_out import (
    IsReleaseNotesFilledOutValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN105_multiple_rns_added import (
    MultipleRNsAddedValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN106_missing_release_notes_for_pack import (
    IsMissingReleaseNotes,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN107_missing_release_notes_entry import (
    IsMissingReleaseNoteEntries,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN108_is_rn_added_to_new_pack import (
    IsRNAddedToNewPackValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN111_is_docker_entry_match_yml import (
    IsDockerEntryMatchYmlValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN112_is_bc_rn_exist import (
    IsBCRNExistValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN113_is_valid_content_type_header import (
    IsValidContentTypeHeaderValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN114_validate_release_notes_header import (
    ReleaseNoteHeaderValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN115_is_valid_rn_headers_format import (
    IsValidRnHeadersFormatValidator,
)
from demisto_sdk.commands.validate.validators.RN_validators.RN116_first_level_header_missing import (
    FirstLevelHeaderMissingValidator,
)


@pytest.mark.parametrize(
    "content_items, expected_number_of_failures, expected_msgs",
    [
        (
            [
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="This is a valid rn.",
                ),  # valid release_note
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="",
                ),  # empty release_note
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%UPDATE_RN%%",
                ),  # shouldn't pass as it has an invalid release note
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%XSIAM_VERSION%%",
                ),  # shouldn't pass as it has an invalid release note
                create_pack_object(
                    paths=["currentVersion"],
                    values=["1.0.0"],
                ),
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%UPDATE_CONTENT_ITEM_CHANGE_DESCRIPTION%%",
                ),  # shouldn't pass as it has an invalid release note
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%UPDATE_CONTENT_ITEM_DESCRIPTION%%",
                ),  # shouldn't pass as it has an invalid release note
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%UPDATE_CONTENT_ITEM_NAME%%",
                ),  # shouldn't pass as it has an invalid release note
                create_pack_object(
                    paths=["currentVersion"],
                    values=["2.0.5"],
                    release_note_content="This is an invalid release note %%UPDATE_CONTENT_ITEM_TYPE%%",
                ),  # shouldn't pass as it has an invalid release note
            ],
            7,
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
        - Case 1: nine pack_metadatas:
            - 1 pack with valid release note.
            - 1 pack with an invalid empty release note.
            - 1 pack with invalid release note.
            - 1 pack with invalid release note.
            - 1 pack without any release notes.
            - 1 pack with invalid release note.
            - 1 pack with invalid release note.
            - 1 pack with invalid release note.
            - 1 pack with invalid release note.

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
            paths=["currentVersion"],
            values=["1.0.1"],
            release_note_content="should fail",
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
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### Integrations\n"
        "##### TestIntegration\n"
        "This is an example\n",
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
        paths=["currentVersion"],
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
        paths=["currentVersion"],
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
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="The new RN",
    )
    old_pack = create_pack_object(
        paths=["currentVersion"],
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
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="some change",
        ),
        create_pack_object(
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="breaking change",
        ),
        create_pack_object(
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="breaking change",
            bc_release_note_content=[{"test": "no breaking change content"}],
        ),
        create_pack_object(
            paths=["currentVersion"],
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


def test_FirstLevelHeaderMissingValidator_obtain_invalid_content_items():
    """
    Given:
    - content_items list with 5 packs, each with RN with different content.
        - Case 1: RN with first and second level header.
        - Case 2: RN with only first level header.
        - Case 3: RN with only second level header.
        - Case 4: RN without first and second level headers.
        - Case 5: RN with force flag header.

    When:
    - Calling the FirstLevelHeaderMissingValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Shouldn't fail anything.
        - Case 2: Shouldn't fail anything.
        - Case 3: Should fail.
        - Case 4: Should fail.
        - Case 5: Shouldn't fail anything.
    """
    content_items = [
        create_pack_object(
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="#### Scripts\n##### script_name\n- Some description.",
        ),
        create_pack_object(
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="#### Scripts\n- Some description.",
        ),
        create_pack_object(
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="##### script_name\n- Some description.",
        ),
        create_pack_object(
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="- Some description.",
        ),
        create_pack_object(
            paths=["currentVersion"],
            values=["2.0.5"],
            release_note_content="## script_name\n- Some description.",
        ),
    ]
    validator = FirstLevelHeaderMissingValidator()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == 2
    expected_msgs = [
        f'The following RN is missing a first level header.\nTo ensure a proper RN structure, please use "demisto-sdk update-release-notes -i Packs/{content_items[2].path.parts[-1]}"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes',
        f'The following RN is missing a first level header.\nTo ensure a proper RN structure, please use "demisto-sdk update-release-notes -i Packs/{content_items[3].path.parts[-1]}"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes',
    ]
    assert all(
        [res_msg in expected_msgs for res_msg in [result.message for result in results]]
    )


def test_IsDockerEntryMatchYmlValidator_fix_same_pack(mocker):
    """
    Given:
    - RN notes with many changes needed to be made in the same pack

    When:
    - Calling the IsDockerEntryMatchYmlValidator fix function.

    Then:
    - All the changes are made and dont conflict with each other
    """

    not_changed_integration = create_integration_object(
        paths=["script.dockerimage", "name"],
        values=["demisto/python3:3.9.7.24070", "NotChanged"],
    )
    old_integration_1 = create_integration_object(
        paths=["script.dockerimage", "name"],
        values=["demisto/python3:3.9.7.24070", "NotChanged"],
    )

    bumped_integration = create_integration_object(
        paths=["script.dockerimage", "name"],
        values=["demisto/python3:3.9.7.24071", "BumpedIntegration"],
    )
    old_integration_2 = create_integration_object(
        paths=["script.dockerimage", "name"],
        values=["demisto/python3:3.9.7.24070", "BumpedIntegration"],
    )

    wrong_bump = create_script_object(
        paths=["dockerimage", "name"],
        values=["demisto/python3:3.9.7.24076", "WrongBump"],
    )
    old_script_1 = create_script_object(
        paths=["dockerimage", "name"],
        values=["demisto/python3:3.9.7.24071", "WrongBump"],
    )
    release_notes = """#### Integration
##### NotChanged
- The next line should be removed
- Updated the Docker image to: *demisto/python3:3.9.7.24071*.
- Something else not related

##### NotBeingFixedDuplicateDocker
- There isnt an object for this, next line shouldnt be changed
- Updated the Docker image to: *demisto/python3:3.9.7.24071*.

##### BumpedIntegration
- Gonna be added below this

##### Another unrelated thing
- Something not related

##### WrongBump
- Updated the Docker image to: *demisto/python3:3.9.7.24075*.
- The above line should be changed to 24076"""
    pack = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=release_notes,
    )
    not_changed_integration.pack = pack
    bumped_integration.pack = pack
    wrong_bump.pack = pack

    content_items = [not_changed_integration, bumped_integration, wrong_bump]
    old_content_items = [
        old_integration_1,
        old_integration_2,
        old_script_1,
    ]
    create_old_file_pointers(content_items, old_content_items)

    mocker.patch(
        "demisto_sdk.commands.content_graph.parsers.related_files.RNRelatedFile.git_status",
        new_callable=mocker.PropertyMock,
        return_value=GitStatuses.ADDED,
    )

    validator = IsDockerEntryMatchYmlValidator()
    fixed_messages = [validator.fix(content_item) for content_item in content_items]
    assert len(fixed_messages) == 3
    expected_msgs = [
        "Removed docker updated entry as it was not changed in the yml.",
        "Added docker updated entry -demisto/python3:3.9.7.24071- in release notes.",
        "Changed docker update entry line in the release notes to match the yml: demisto/python3:3.9.7.24076.",
    ]
    assert all(
        [
            res_msg in expected_msgs
            for res_msg in [result.message for result in fixed_messages]
        ]
    )

    expected_rn = """#### Integration
##### NotChanged
- The next line should be removed
- Something else not related

##### NotBeingFixedDuplicateDocker
- There isnt an object for this, next line shouldnt be changed
- Updated the Docker image to: *demisto/python3:3.9.7.24071*.

##### BumpedIntegration
- Gonna be added below this
- Updated the Docker image to: *demisto/python3:3.9.7.24071*.

##### Another unrelated thing
- Something not related

##### WrongBump
- Updated the Docker image to: *demisto/python3:3.9.7.24076*.
- The above line should be changed to 24076"""
    assert pack.release_note.file_content == expected_rn


def test_IsDockerEntryMatchYmlValidator_fix(mocker):
    """
    Given:
    - content_items list with 5 packs, each with RN with different content.
        - Case 1: A script that modified with wrong image in rn.
        - Case 2: A script that said didnt modified with rn
        - Case 3: A script that modified without adding rn.

    When:
    - Calling the IsDockerEntryMatchYmlValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Switch the image.
        - Case 2: Remove the line.
        - Case 3: Add the line.
    """
    integration_1 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    old_integration_1 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24070"]
    )
    pack_1 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Integration\n##### {integration_1.name}\n- Updated the Docker image to: *demisto/python3:3.9.7.24076*.",
    )
    integration_2 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    old_integration_2 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    pack_2 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Integration\n##### {integration_2.name}\n- Updated the Docker image to: *demisto/python3:3.9.7.24071*.\n- Something not related.",
    )
    script_1 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24076"]
    )
    old_script_1 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    pack_3 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Scripts\n##### {script_1.name}\n- Something not related.",
    )

    integration_1.pack = pack_1
    integration_2.pack = pack_2
    script_1.pack = pack_3

    content_items = [integration_1, integration_2, script_1]
    old_content_items = [
        old_integration_1,
        old_integration_2,
        old_script_1,
    ]
    mocker.patch(
        "demisto_sdk.commands.content_graph.parsers.related_files.RNRelatedFile.git_status",
        new_callable=mocker.PropertyMock,
        return_value=GitStatuses.ADDED,
    )
    create_old_file_pointers(content_items, old_content_items)
    validator = IsDockerEntryMatchYmlValidator()
    fixed_messages = [validator.fix(content_item) for content_item in content_items]
    assert len(fixed_messages) == 3
    expected_msgs = [
        "Changed docker update entry line in the release notes to match the yml: demisto/python3:3.9.7.24071.",
        "Removed docker updated entry as it was not changed in the yml.",
        "Added docker updated entry -demisto/python3:3.9.7.24076- in release notes.",
    ]
    assert all(
        [
            res_msg in expected_msgs
            for res_msg in [result.message for result in fixed_messages]
        ]
    )
    assert (
        pack_1.release_note.file_content
        == "#### Integration\n##### TestIntegration\n- Updated the Docker image to: *demisto/python3:3.9.7.24071*."
    )
    assert (
        pack_2.release_note.file_content
        == "#### Integration\n##### TestIntegration\n- Something not related."
    )
    assert (
        pack_3.release_note.file_content
        == "#### Scripts\n##### myScript\n- Something not related.\n- Updated the Docker image to: *demisto/python3:3.9.7.24076*."
    )


@pytest.mark.parametrize(
    "git_status, expected_msgs, expected_number_of_failures",
    [
        (
            GitStatuses.ADDED,
            [
                "The release notes regarding the docker image are not correct. Docker version in release notes should be demisto/python3:3.9.7.24071, found: demisto/python3:3.9.7.24076",
                "The release notes regarding the docker image are not correct. Docker version in release notes should be demisto/python3:3.9.7.24076, found: No docker entry found",
                "The release notes regarding the docker image are not correct. There should be no release notes docker update entry, found: demisto/python3:3.9.7.24076",
            ],
            3,
        ),
        (None, [], 0),
    ],
)
def test_IsDockerEntryMatchYmlValidator_obtain_invalid_content_items(
    mocker, git_status, expected_msgs, expected_number_of_failures
):
    """
    Given:
    - content_items list with 5 packs, each with RN with different content.
        - pack 1: An integration with modified docker where the docker image entry doesn't match the version in the rn.
        - pack 2: An integration without docker modification.
        - pack 3: A script with modified docker where the docker image entry in the rn match the on in the yml.
        - pack 4: A script with modified docker where no docker image entry appear in the rn.
        - pack 5: A script that didn't modify the docker an RN that says it did
        Split into two cases:
        - Case 1: The RNs were Added.
        - Case 2: The RNs git status is None (i.e no new rn).

    When:
    - Calling the IsDockerEntryMatchYmlValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: packs 1, 4, and 5 should fail.
        - Case 2: No failures.
    """
    integration_1 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    old_integration_1 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24070"]
    )
    pack_1 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Integration\n##### {integration_1.name}\n- Updated the Docker image to: *demisto/python3:3.9.7.24076*.",
    )
    integration_2 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    old_integration_2 = create_integration_object(
        paths=["script.dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    pack_2 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Integration\n##### {integration_2.name}\n- entry not related to docker update.",
    )
    script_1 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24076"]
    )
    old_script_1 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    pack_3 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Scripts\n##### {script_1.name}\n- Updated the Docker image to: *demisto/python3:3.9.7.24076*.",
    )
    script_2 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24076"]
    )
    old_script_2 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24071"]
    )
    pack_4 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Scripts\n##### {script_2.name}\n- Entry not related to docker image update.",
    )
    script_3 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24076"]
    )
    old_script_3 = create_script_object(
        paths=["dockerimage"], values=["demisto/python3:3.9.7.24076"]
    )
    pack_5 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content=f"#### Scripts\n##### {script_2.name}\n- Updated the Docker image to: *demisto/python3:3.9.7.24076*.",
    )
    mocker.patch(
        "demisto_sdk.commands.content_graph.parsers.related_files.RNRelatedFile.git_status",
        new_callable=mocker.PropertyMock,
        return_value=git_status,
    )
    integration_1.pack = pack_1
    integration_2.pack = pack_2
    script_1.pack = pack_3
    script_2.pack = pack_4
    script_3.pack = pack_5
    content_items = [integration_1, integration_2, script_1, script_2, script_3]
    old_content_items = [
        old_integration_1,
        old_integration_2,
        old_script_1,
        old_script_2,
        old_script_3,
    ]
    create_old_file_pointers(content_items, old_content_items)
    validator = IsDockerEntryMatchYmlValidator()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == expected_number_of_failures
    assert all(
        [res_msg in expected_msgs for res_msg in [result.message for result in results]]
    )


def test_IsValidContentTypeHeaderValidator_obtain_invalid_content_items():
    """
    Given:
    - content_items list with 5 packs, each with RN with different content.
        - Case 1: RN with 2 invalid content type headers.
        - Case 2: RN with 1 invalid and 1 valid content type headers.
        - Case 3: RN with 2 valid content type headers.
    When:
    - Calling the IsValidContentTypeHeaderValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Should fail.
        - Case 2: Should fail.
        - Case 3: Shouldn't fail anything.
    """
    pack_1 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### FakeContentType_1\n##### FakeContentItem_1\nFake comment.\n#### FakeContentType_2\n##### FakeContentItem_1\nFake comment.",
    )
    pack_2 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### FakeContentType_1\n##### FakeContentItem_1\nFake comment.\n#### Integrations\n##### Test integration\ntest.",
    )
    pack_3 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### Scripts\n##### Test script\ntest.\n#### Integrations\n##### Test integration\ntest.",
    )
    content_items = [pack_1, pack_2, pack_3]
    validator = IsValidContentTypeHeaderValidator()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == 2
    expected_msgs = [
        'The following content type header(s) "FakeContentType_1, FakeContentType_2" are invalid.\nPlease use "demisto-sdk update-release-notes -i Packs/HelloWorld"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes',
        'The following content type header(s) "FakeContentType_1" are invalid.\nPlease use "demisto-sdk update-release-notes -i Packs/HelloWorld"\nFor more information, refer to the following documentation: https://xsoar.pan.dev/docs/documentation/release-notes',
    ]
    assert all(
        [res_msg in expected_msgs for res_msg in [result.message for result in results]]
    )


@pytest.fixture
def mock_is_missing_rn_validator(mocker):
    """simplified validator methods for testing"""
    for rn_validator in [
        "RN106_missing_release_notes_for_pack",
        "RN107_missing_release_notes_entry",
    ]:
        mocker.patch(
            f"demisto_sdk.commands.validate.validators.RN_validators.{rn_validator}.should_skip_rn_check",
            side_effect=lambda c: isinstance(c, TestPlaybook) or c.is_silent,
        )
        mocker.patch(
            f"demisto_sdk.commands.validate.validators.RN_validators.{rn_validator}.was_rn_added",
            side_effect=lambda p: bool(p.release_note.file_content),  # type: ignore
        )


@pytest.fixture
def mock_graph(mocker):
    mocker.patch(
        "demisto_sdk.commands.validate.validators.base_validator.update_content_graph"
    )
    mocker.patch.object(ContentGraphInterface, "__init__", return_value=None)
    mocker.patch.object(
        ContentGraphInterface, "__enter__", return_value=ContentGraphInterface
    )
    mocker.patch.object(ContentGraphInterface, "__exit__", return_value=None)


def test_IsMissingReleaseNotes(mock_is_missing_rn_validator):
    """
    Given:
    - pack1 with a changed integration, a release notes file exists
    - pack2 with a changed script, a release notes file does not exist
    - pack3 with a changed test playbook, a release notes file exist does not exist
    - pack4 - a new pack with a script, a RN file does not exist
    When:
    - Calling IsMissingReleaseNotes.obtain_invalid_content_items().
    Then:
    - Ensure only one validation error is returned for pack2 with the changed script.

    """
    pack1 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
        release_note_content="this is a rn",
    )
    integ = create_integration_object()
    integ.pack = pack1

    pack2 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
    )
    script = create_script_object()
    script.pack = pack2

    pack3 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
    )
    tpb = create_test_playbook_object()
    tpb.pack = pack3

    pack4 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.0"],
    )
    pack4.git_status = GitStatuses.ADDED
    script2 = create_script_object()
    script2.pack = pack4

    content_items = [pack1, integ, pack2, script, pack3, tpb, pack4, script2]
    validator = IsMissingReleaseNotes()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == 1
    assert results[0].content_object == pack2
    assert pack2.object_id in results[0].message


def test_IsMissingReleaseNotes_for_api_module_dependents(
    mocker,
    mock_graph,
    mock_is_missing_rn_validator,
):
    """
    Given:
    - A change in an API module imported by three integrations from three different packs.
        - Pack 1 has a release note.
        - Packs 2 and 3 do not have a release note.
    When:
    - Calling IsMissingReleaseNotes.obtain_invalid_content_items().
    Then:
    - Ensure two validation error are returned.
    - Ensure we recommend to run update-release-notes on ApiModules pack.

    """
    pack1 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
        release_note_content="this is a rn",
    )
    integ1 = create_integration_object()
    integ1.pack = pack1

    pack2 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
    )
    integ2 = create_integration_object()
    integ2.pack = pack2

    pack3 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
    )
    integ3 = create_integration_object()
    integ3.pack = pack3

    api_modules_pack = create_pack_object(
        name=API_MODULES_PACK,
        paths=["name"],
        values=[API_MODULES_PACK],
    )
    api_module = create_script_object()
    api_module.pack = api_modules_pack
    mocker.patch.object(
        ContentGraphInterface,
        "get_api_module_imports",
        return_value=[integ1, integ2, integ3],
    )

    content_items = [
        pack1,
        integ1,
        pack2,
        integ2,
        api_module,
        api_modules_pack,
        pack3,
        integ3,
    ]
    validator = IsMissingReleaseNotes()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == 2
    assert results[0].content_object == pack2
    assert results[1].content_object == pack3
    assert all(API_MODULES_PACK in result.message for result in results)


def test_IsMissingReleaseNoteEntries(mock_is_missing_rn_validator):
    """
    Given:
    - pack1 with a modified integration and silent playbook, a RN entry exists only for the integration
    - pack2 with modified script, playbook and TPB, a RN entry exists only for the script
    - pack3 with a modified script, a RN file does not exist
    - pack4 with a new mapper, a RN exists
    When:
    - Calling IsMissingReleaseNotes.obtain_invalid_content_items().
    Then:
    - Ensure one validation error is raised due to the missing RN entry for the playbook.
    - pack3 will not raise a RN107 validation error since it should be raised for RN106.

    """
    integ = create_integration_object()
    pack1 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
        release_note_content=f"#### Integrations\n##### {integ.display_name}\n- Added x y z",
    )
    integ.pack = pack1
    silent_playbook = create_playbook_object()
    silent_playbook.is_silent = True
    silent_playbook.pack = pack1

    script1 = create_script_object()
    playbook = create_playbook_object()
    tpb = create_test_playbook_object()
    pack2 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
        release_note_content=f"#### Scripts\n##### {script1.display_name}\n- Added x y z",
    )
    script1.pack = pack2
    playbook.pack = pack2
    tpb.pack = pack2

    pack3 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
    )
    script2 = create_script_object()
    script2.pack = pack3

    mapper = create_incoming_mapper_object()
    pack4 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
        release_note_content=f"#### Mappers\n##### New: {mapper.display_name}\n- Added x y z",
    )
    mapper.pack = pack4

    content_items = [
        pack1,
        integ,
        silent_playbook,
        pack2,
        script1,
        playbook,
        tpb,
        pack3,
        script2,
        pack4,
        mapper,
    ]
    validator = IsMissingReleaseNoteEntries()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == 1
    assert results[0].content_object == playbook


def test_IsMissingReleaseNoteEntries_for_api_module_dependents(
    mocker,
    mock_graph,
    mock_is_missing_rn_validator,
):
    """
    Given:
    - A change in an API module imported by three integrations from three different packs.
        - Integration of pack 1 has a RN entry.
        - Pack 2 has a release note file, but not a RN entry for its integration.
        - Pack 3 does not have a release note file.
    When:
    - Calling IsMissingReleaseNotes.obtain_invalid_content_items().
    Then:
    - Ensure one validation error is raised due to the missing RN entry for the integration of pack 2.

    """
    integ1 = create_integration_object()
    pack1 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
        release_note_content=f"#### Integrations\n##### {integ1.display_name}\n- Added x y z",
    )
    integ1.pack = pack1

    integ2 = create_integration_object()
    pack2 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
        release_note_content="#### Scripts\n##### Dummy Script\n- Added x y z",
    )
    integ2.pack = pack2

    integ3 = create_integration_object()
    pack3 = create_pack_object(
        paths=["currentVersion"],
        values=["1.0.1"],
    )
    integ3.pack = pack3

    api_modules_pack = create_pack_object(
        name=API_MODULES_PACK,
        paths=["name"],
        values=[API_MODULES_PACK],
    )
    api_module = create_script_object()
    api_module.pack = api_modules_pack
    mocker.patch.object(
        ContentGraphInterface,
        "get_api_module_imports",
        return_value=[integ1, integ2, integ3],
    )

    content_items = [
        pack1,
        integ1,
        pack2,
        integ2,
        api_module,
        api_modules_pack,
        pack3,
        integ3,
    ]
    validator = IsMissingReleaseNoteEntries()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == 1
    assert results[0].content_object == integ2


def test_IsValidRnHeadersFormatValidator_obtain_invalid_content_items():
    """
    Given:
    - content_items list with 5 packs, each with RN with different content.
        - Case 1: RN with valid second level header "integration-test" starting with 5 #'s.
        - Case 2: RN with valid second level header "Test" starting with 5 #'s.
        - Case 3: RN with invalid second level header "Test" starting with 5 #'s followed by several spaces.
        - Case 4: RN with invalid second level header "integration-test" surrounded by '**'.
        - Case 5: RN with invalid second level header "test" surrounded by '**'.
        - Case 6: RN with headers in the playbook RN format.
    When:
    - Calling the IsValidRnHeadersFormatValidator obtain_invalid_content_items function.

    Then:
    - Make sure the right amount of pack metadata failed, and that the right error message is returned.
        - Case 1: Should pass.
        - Case 2: Should pass.
        - Case 3: Should fail.
        - Case 4: Should fail.
        - Case 5: Should fail.
        - Case 6: Should pass.
    """
    pack_1 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### Integrations\n##### integration-test\n- Added x y z",
    )
    pack_2 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### FakeContentType\n##### Test\n- Added x y z",
    )
    pack_3 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### Incident Fields\n    ##### Test\n    - Added x y z",
    )
    pack_4 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### Integrations\n- **integration-test**\n- Added x y z",
    )
    pack_5 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### Incident Fields\n- **test**\n- Added x y z",
    )
    pack_6 = create_pack_object(
        paths=["currentVersion"],
        values=["2.0.5"],
        release_note_content="#### Playbooks\n##### New: name\n##### Playbook Stages:\n- Added x y z",
    )
    content_items = [pack_1, pack_2, pack_3, pack_4, pack_5, pack_6]
    validator = IsValidRnHeadersFormatValidator()
    results = validator.obtain_invalid_content_items(content_items)
    assert len(results) == 3
    expected_msgs = [
        "Did not find content items headers under the following content types: Incident Fields. This might be due to invalid format.",
        "Did not find content items headers under the following content types: Integrations. This might be due to invalid format.",
        "Did not find content items headers under the following content types: Incident Fields. This might be due to invalid format.",
    ]
    assert all(
        [
            expected_msg in result.message
            for result, expected_msg in zip(results, expected_msgs)
        ]
    )
