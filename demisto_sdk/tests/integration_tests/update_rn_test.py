import os

from demisto_sdk.commands.validate.file_validator import FilesValidator
from TestSuite.test_tools import ChangeCWD


def mock_git(mocker, added_files):
    mocker.patch.object(FilesValidator, 'get_current_working_branch', return_value='branch name')
    mocker.patch.object(FilesValidator, 'get_modified_and_added_files', return_value=added_files)


def create_integration_and_release_notes(pack, update_type, idx, update_rn_content=True):
    pack.create_integration('FakeIntegration_' + str(idx))
    pack.update_release_notes(update_type)
    if update_rn_content:
        pack.release_notes[idx].fill('This is a release note.')


def is_release_note_valid(mocker, pack, idx):
    # mocking the git functionality (otherwise it'll raise an error)
    mock_git(mocker, added_files=set([pack.integrations[idx].yml_path]))
    files_validator = FilesValidator(use_git=True)
    files_validator.is_valid_release_notes(pack.release_notes[idx].file_path)
    return files_validator._is_valid


def test_update_release_notes(mocker, repo):
    """
    Given
    - A valid pack with integrations.

    When
    - Updating release notes.

    Then
    - Ensure release notes update is valid.
    """
    pack = repo.create_pack('FakePack')
    with ChangeCWD(pack.repo_path):
        create_integration_and_release_notes(pack, 'revision', idx=0)
        assert is_release_note_valid(mocker, pack, idx=0)
        assert '1_0_1.md' in os.listdir(os.path.join(pack.path, 'ReleaseNotes'))

        create_integration_and_release_notes(pack, 'minor', idx=1)
        assert is_release_note_valid(mocker, pack, idx=1)
        assert '1_1_0.md' in os.listdir(os.path.join(pack.path, 'ReleaseNotes'))

        # without updating the release notes file, the validator should fail
        create_integration_and_release_notes(pack, 'major', idx=2, update_rn_content=False)
        assert not is_release_note_valid(mocker, pack, idx=2)
        assert '2_0_0.md' in os.listdir(os.path.join(pack.path, 'ReleaseNotes'))

