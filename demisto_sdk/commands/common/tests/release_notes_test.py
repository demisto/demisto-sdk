import os

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.release_notes import \
    ReleaseNotesValidator


def get_validator(file_path=''):
    release_notes_validator = ReleaseNotesValidator("")
    release_notes_validator.file_path = file_path
    release_notes_validator.release_notes_path = file_path
    release_notes_validator.latest_release_notes = file_path
    return release_notes_validator


FILES_PATH = os.path.normpath(os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
nothing_in_rn = ''
rn_not_filled_out = '%%UPDATE_RN%%'
rn_filled_out = 'This are sample release notes'
diff_package = [(nothing_in_rn, False),
                (rn_not_filled_out, False),
                (rn_filled_out, True)]


@pytest.mark.parametrize('release_notes, expected_result', diff_package)
def test_rn_master_diff(release_notes, expected_result, mocker):
    """
    Given
    - Case 1: Empty release notes.
    - Case 2: Not filled out release notes.
    - Case 3: Valid release notes

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should return the prompt "Please complete the release notes found at: {path}" and
              return False
    - Case 2: Should return the prompt "Please finish filling out the release notes found at: {path}" and
              return False
    - Case 3: Should print nothing and return True
    """
    mocker.patch.object(ReleaseNotesValidator, '__init__', lambda a, b: None)
    validator = get_validator(release_notes)
    assert validator.is_file_valid() == expected_result


def test_init():
    """
    Given
    - Release notes file path

    When
    - Running validation on release notes.

    Then
    - Ensure init returns valid file path and release notes contents.
    """
    filepath = os.path.join(FILES_PATH, 'ReleaseNotes', '1_1_1.md')
    release_notes_validator = ReleaseNotesValidator(filepath)
    release_notes_validator.file_path = 'demisto_sdk/tests/test_files/ReleaseNotes/1_1_1.md'
    assert release_notes_validator.release_notes_path == filepath
    assert release_notes_validator.latest_release_notes == '### Test'
