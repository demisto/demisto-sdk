import os
from os.path import join

import pytest
from click.testing import CliRunner

import conftest  # noqa: F401
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from demisto_sdk.commands.update_release_notes.update_rn_manager import \
    UpdateReleaseNotesManager
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from TestSuite.test_tools import ChangeCWD

UPDATE_RN_COMMAND = "update-release-notes"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
TEST_FILES_PATH = join(git_path(), 'demisto_sdk', 'tests')
AZURE_FEED_PACK_PATH = join(TEST_FILES_PATH, 'test_files', 'content_repo_example', 'Packs', 'FeedAzureValid')
RN_FOLDER = join(git_path(), 'Packs', 'FeedAzureValid', 'ReleaseNotes')
VMWARE_PACK_PATH = join(TEST_FILES_PATH, 'test_files', 'content_repo_example', 'Packs', 'VMware')
VMWARE_RN_PACK_PATH = join(git_path(), 'Packs', 'VMware', 'ReleaseNotes')
THINKCANARY_RN_FOLDER = join(git_path(), 'Packs', 'ThinkCanary', 'ReleaseNotes')


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

    expected_rn = '\n' + '#### Integrations\n' + \
                  '##### New: Azure Feed\n' + \
                  '- Azure.CloudIPs Feed Integration. (Available from Cortex XSOAR 5.5.0).\n'

    added_files = {join(AZURE_FEED_PACK_PATH, 'Integrations', 'FeedAzureValid', 'FeedAzureValid.yml')}
    rn_path = join(RN_FOLDER, '1_0_1.md')
    runner = CliRunner(mix_stderr=True)
    mocker.patch('demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_name',
                 return_value='FeedAzureValid')
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='FeedAzureValid')
    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git', return_value=(set(), added_files, set(), set()))
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='1.0.0')

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

    expected_rn = '\n' + '#### Integrations\n' + \
                  '##### Azure Feed\n' + \
                  '- %%UPDATE_RN%%\n'
    modified_files = {join(AZURE_FEED_PACK_PATH, 'Integrations', 'FeedAzureValid', 'FeedAzureValid.yml')}
    rn_path = join(RN_FOLDER, '1_0_1.md')

    runner = CliRunner(mix_stderr=False)
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='FeedAzureValid')

    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git', return_value=(modified_files, set(),
                                                                                     set(), set()))
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='1.0.0')

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

    expected_rn = '\n' + '#### Incident Fields\n' + \
                  '- **City**\n'

    runner = CliRunner(mix_stderr=False)
    modified_files = {join(AZURE_FEED_PACK_PATH, 'IncidentFields', 'incidentfield-city.json')}
    rn_path = join(RN_FOLDER, '1_0_1.md')
    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git', return_value=(modified_files, set(),
                                                                                     set(), set()))
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='FeedAzureValid')
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='1.0.0')

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


def test_update_release_notes_unified_yml_integration(demisto_client, mocker):
    """
    Given
    - VMware pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """

    expected_rn = '\n' + '#### Integrations\n' + \
                  '##### VMware\n' + \
                  '- %%UPDATE_RN%%\n'

    runner = CliRunner(mix_stderr=False)
    old_files = {join(VMWARE_PACK_PATH, 'Integrations', 'integration-VMware.yml')}
    rn_path = join(VMWARE_RN_PACK_PATH, '1_0_1.md')
    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git', return_value=(set(), set(), set(), old_files))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='VMware')
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='1.0.0')

    if os.path.exists(rn_path):
        os.remove(rn_path)

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'VMware')])
    assert result.exit_code == 0
    assert not result.exception
    assert 'Changes were detected. Bumping VMware to version: 1.0.1' in result.stdout
    assert 'Finished updating release notes for VMware.' in result.stdout

    assert os.path.isfile(rn_path)
    with open(rn_path, 'r') as f:
        rn = f.read()
    assert expected_rn == rn


def test_update_release_notes_non_content_path(demisto_client, mocker):
    """
    Given
    - non content pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure an error is raised
    """
    runner = CliRunner(mix_stderr=False)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git', side_effect=FileNotFoundError)
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='VMware')
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='1.0.0')

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Users', 'MyPacks', 'VMware')])

    assert result.exit_code == 1
    assert result.exception
    assert "You are not running" in result.stdout  # check error str is in stdout


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
    expected_rn = '\n' + '#### Integrations\n' + \
                  '##### New: Azure Feed\n' + \
                  '- Azure.CloudIPs Feed Integration.\n' + \
                  '\n' + '#### Incident Fields\n' + \
                  '- **City**'

    input_rn = '\n' + '#### Integrations\n' + \
               '##### New: Azure Feed\n' + \
               '- Azure.CloudIPs Feed Integration.\n'

    rn_path = join(RN_FOLDER, '1_0_0.md')
    modified_files = {join(AZURE_FEED_PACK_PATH, 'IncidentFields', 'incidentfield-city.json')}
    with open(rn_path, 'w') as file_:
        file_.write(input_rn)

    runner = CliRunner(mix_stderr=False)

    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=False)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git', return_value=(modified_files, set(),
                                                                                     set(), set()))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='1.0.0')
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='FeedAzureValid')
    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'FeedAzureValid')])

    assert result.exit_code == 0
    assert os.path.exists(rn_path)
    assert not result.exception
    assert 'Finished updating release notes for FeedAzureValid.' in result.stdout

    with open(rn_path, 'r') as f:
        rn = f.read()
    os.remove(rn_path)
    assert expected_rn == rn


def test_update_release_notes_modified_apimodule(demisto_client, repo, mocker):
    """
    Given
    - ApiModules_script.yml which is part of APIModules pack was changed.
    - FeedTAXII pack path exists and uses ApiModules_script
    - id_set.json indicates FeedTAXII uses APIModules

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors for APIModule and related pack FeedTAXII:
    - Ensure message is printed when update release notes process finished.
    """
    repo.setup_one_pack("ApiModules")
    api_module_pack = repo.packs[0]
    api_module_script_path = join(api_module_pack.path, "Scripts/ApiModules_script/ApiModules_script.yml")

    repo.setup_one_pack("FeedTAXII")
    taxii_feed_pack = repo.packs[1]
    taxii_feed_integration_path = join(taxii_feed_pack.path,
                                       "Integrations/FeedTAXII_integration/FeedTAXII_integration.yml")
    repo.id_set.update({
        "scripts": [
            {
                "ApiModules_script": {
                    "name": "ApiModules_script",
                    "file_path": api_module_script_path,
                    "pack": "ApiModules"
                }
            }
        ],
        "integrations": [
            {
                "FeedTAXII_integration": {
                    "name": "FeedTAXII_integration",
                    "file_path": taxii_feed_integration_path,
                    "pack": "FeedTAXII",
                    "api_modules": "ApiModules_script"
                }
            }
        ]
    })

    modified_files = {api_module_script_path}
    runner = CliRunner(mix_stderr=False)

    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git', return_value=(modified_files, set(),
                                                                                     set(), set()))
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='ApiModules')
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='1.0.0')

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'ApiModules'), "-idp", repo.id_set.path])

    assert result.exit_code == 0
    assert not result.exception
    assert 'Release notes are not required for the ApiModules pack since this pack is not versioned.' in result.stdout
    assert 'Changes were detected. Bumping FeedTAXII to version: 1.0.1' in result.stdout


def test_update_release_on_matadata_change(demisto_client, mocker, repo):
    """
    Given
    - change only in metadata

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure not find changes which would belong in release notes .
    """
    pack = repo.create_pack('FeedAzureValid')
    pack.pack_metadata.write_json(open('demisto_sdk/tests/test_files/1.pack_metadata.json').read())

    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(UpdateReleaseNotesManager, 'get_git_changed_files',
                        return_value=(set(), set(), {pack.pack_metadata.path}, set()))
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='FeedAzureValid')
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_names_from_files', return_value={'FeedAzureValid'})

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UPDATE_RN_COMMAND, "-g"])
        print(result.stdout)
    assert result.exit_code == 0
    assert 'No changes that require release notes were detected. If such changes were made, ' \
           'please commit the changes and rerun the command' in result.stdout


def test_update_release_notes_master_ahead_of_current(demisto_client, mocker, repo):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure the new version is taken from master and not from local metadata file.
    """
    modified_files = {join(AZURE_FEED_PACK_PATH, 'IncidentFields', 'incidentfield-city.json')}
    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(UpdateReleaseNotesManager, 'get_git_changed_files',
                        return_value=(modified_files, {'1_1_0.md'}, set(), set()))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='FeedAzureValid')
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='2.0.0')

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'FeedAzureValid')])
    assert result.exit_code == 0
    assert not result.exception
    assert 'Changes were detected. Bumping FeedAzureValid to version: 2.0.1' in result.stdout
    assert 'Finished updating release notes for FeedAzureValid.' in result.stdout


def test_update_release_notes_master_unavailable(demisto_client, mocker, repo):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure the new version is taken from local metadata file.
    """

    modified_files = {join(AZURE_FEED_PACK_PATH, 'Integrations', 'FeedAzureValid', 'FeedAzureValid.yml')}
    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(UpdateReleaseNotesManager, 'get_git_changed_files',
                        return_value=(modified_files, {'1_1_0.md'}, set(), set()))
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.1.0'})
    mocker.patch('demisto_sdk.commands.common.tools.get_pack_name', return_value='FeedAzureValid')
    mocker.patch.object(UpdateRN, 'get_master_version', return_value='0.0.0')
    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'FeedAzureValid')])
    assert result.exit_code == 0
    assert not result.exception
    assert 'Changes were detected. Bumping FeedAzureValid to version: 1.1.1' in result.stdout
    assert 'Finished updating release notes for FeedAzureValid.' in result.stdout


def test_force_update_release_no_pack_given(demisto_client, repo):
    """
        Given
        - Nothing have changed.

        When
        - Running demisto-sdk update-release-notes command with --force flag but no specific pack is given.

        Then
        - Ensure that an error is printed.
    """
    runner = CliRunner(mix_stderr=True)
    result = runner.invoke(main, [UPDATE_RN_COMMAND, "--force"])
    assert 'Please add a specific pack in order to force' in result.stdout


def test_force_update_release(demisto_client, mocker, repo):
    """
    Given
    - Nothing have changed.

    When
    - Running demisto-sdk update-release-notes command with --force flag.

    Then
    - Ensure that RN were updated.
    """
    rn_path = join(THINKCANARY_RN_FOLDER, '1_0_1.md')
    if os.path.exists(rn_path):
        os.remove(rn_path)
    mocker.patch.object(UpdateRN, 'is_bump_required', return_value=True)
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git',
                        return_value=(set(), set(), set(), set()))
    mocker.patch.object(ValidateManager, 'setup_git_params', return_value='')
    mocker.patch.object(GitUtil, 'get_current_working_branch', return_value="branch_name")
    mocker.patch.object(UpdateRN, 'get_pack_metadata', return_value={'currentVersion': '1.0.0'})
    mocker.patch('demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_name',
                 return_value='ThinkCanary')
    mocker.patch('demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_names_from_files',
                 return_value={'ThinkCanary'})

    runner = CliRunner(mix_stderr=True)
    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join('Packs', 'ThinkCanary'), "--force"])
    assert 'Bumping ThinkCanary to version: 1.0.1' in result.stdout
    assert 'Finished updating release notes for ThinkCanary.' in result.stdout

    with open(rn_path, 'r') as f:
        rn = f.read()
    assert '##### ThinkCanary\n- %%UPDATE_RN%%\n' == rn
