import os
from os.path import join

import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from demisto_sdk.commands.validate.validate_manager import ValidateManager

UPDATE_RN_COMMAND = "update-release-notes"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
TEST_FILES_PATH = join(git_path(), 'demisto_sdk', 'tests')
AZURE_FEED_PACK_PATH = join(TEST_FILES_PATH, 'test_files', 'content_repo_example', 'Packs', 'FeedAzureValid')
RN_FOLDER = join(git_path(), 'Packs', 'FeedAzureValid', 'ReleaseNotes')


@pytest.fixture
def demisto_client(mocker):
    mocker.patch(
        "demisto_sdk.commands.download.downloader.demisto_client",
        return_valure="object"
    )


def test_update_release_notes_new_integration(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """

    expected_rn = '\n' + '#### Integrations\n' +\
                  '##### New: Azure Feed\n' + \
                  '- Azure.CloudIPs Feed Integration.\n'

    added_files = {join(AZURE_FEED_PACK_PATH, 'Integrations', 'FeedAzureValid', 'FeedAzureValid.yml')}
    rn_path = join(RN_FOLDER, '1_0_1.md')
    runner = CliRunner(mix_stderr=False)

    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(set(), added_files,
                                                                                       set(), set(), set()))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})

    if os.path.exists(rn_path):
        os.remove(rn_path)

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'FeedAzureValid')])

    assert result.exit_code == 0
    assert os.path.isfile(rn_path)
    assert not result.exception
    assert 'Changes were detected. Bumping FeedAzureValid to version: 1.0.1' in result.stdout
    assert 'Finished updating release notes for FeedAzureValid.' in result.stdout

    with open(rn_path, 'r') as f:
        rn = f.read()
    assert expected_rn == rn


def test_update_release_notes_modified_integration(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """

    expected_rn = '\n' + '#### Integrations\n' +\
                  '##### Azure Feed\n' + \
                  '- %%UPDATE_RN%%\n'
    modified_files = {join(AZURE_FEED_PACK_PATH, 'Integrations', 'FeedAzureValid', 'FeedAzureValid.yml')}
    rn_path = join(RN_FOLDER, '1_0_1.md')

    runner = CliRunner(mix_stderr=False)

    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(modified_files, set(),
                                                                                       set(), set(), set()))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})

    if os.path.exists(rn_path):
        os.remove(rn_path)

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'FeedAzureValid')])

    assert result.exit_code == 0
    assert os.path.isfile(rn_path)
    assert not result.exception
    assert 'Changes were detected. Bumping FeedAzureValid to version: 1.0.1' in result.stdout
    assert 'Finished updating release notes for FeedAzureValid.' in result.stdout

    with open(rn_path, 'r') as f:
        rn = f.read()
    assert expected_rn == rn


def test_update_release_notes_incident_field(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """

    expected_rn = '\n' + '#### Incident Fields\n' +\
                  '- **City**\n'

    runner = CliRunner(mix_stderr=False)
    modified_files = {join(AZURE_FEED_PACK_PATH, 'IncidentFields', 'incidentfield-city.json')}
    rn_path = join(RN_FOLDER, '1_0_1.md')
    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(modified_files, set(),
                                                                                       set(), set(), set()))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})

    if os.path.exists(rn_path):
        os.remove(rn_path)

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'FeedAzureValid')])

    assert result.exit_code == 0
    assert os.path.isfile(rn_path)
    assert not result.exception
    assert 'Changes were detected. Bumping FeedAzureValid to version: 1.0.1' in result.stdout
    assert 'Finished updating release notes for FeedAzureValid.' in result.stdout

    with open(rn_path, 'r') as f:
        rn = f.read()
    assert expected_rn == rn


def test_update_release_notes_existing(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file updated with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """
    expected_rn = '\n' + '#### Integrations\n' +\
                  '##### New: Azure Feed\n' + \
                  '- Azure.CloudIPs Feed Integration.\n' + \
                  '\n' + '#### Incident Fields\n' + \
                  '- **City**'

    input_rn = '\n' + '#### Integrations\n' +\
               '##### New: Azure Feed\n' + \
               '- Azure.CloudIPs Feed Integration.\n'

    rn_path = join(RN_FOLDER, '1_0_0.md')
    modified_files = {join(AZURE_FEED_PACK_PATH, 'IncidentFields', 'incidentfield-city.json')}
    with open(rn_path, 'w') as file_:
        file_.write(input_rn)

    runner = CliRunner(mix_stderr=False)

    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=False)
    mocker.patch.object(ValidateManager, 'get_modified_and_added_files', return_value=(modified_files, set(),
                                                                                       set(), set(), set()))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'FeedAzureValid')])

    assert result.exit_code == 0
    assert os.path.exists(rn_path)
    assert not result.exception
    assert 'Finished updating release notes for FeedAzureValid.' in result.stdout

    with open(rn_path, 'r') as f:
        rn = f.read()
    os.remove(rn_path)
    assert expected_rn == rn
