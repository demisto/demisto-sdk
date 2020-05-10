import pytest
from demisto_sdk.commands.common.hook_validations.release_notes import \
    ReleaseNotesValidator


def get_validator(file_path=''):
    release_notes_validator = ReleaseNotesValidator("")
    release_notes_validator.file_path = file_path
    release_notes_validator.release_notes_path = file_path
    release_notes_validator.latest_release_notes = file_path
    return release_notes_validator


nothing_in_rn = ''
rn_not_filled_out = '%%UPDATE_RN%%'
rn_filled_out = 'This are sample release notes'
diff_package = [(nothing_in_rn, False),
                (rn_not_filled_out, False),
                (rn_filled_out, True)]


@pytest.mark.parametrize('release_notes, expected_result', diff_package)
def test_rn_master_diff(release_notes, expected_result, mocker):
    mocker.patch.object(ReleaseNotesValidator, '__init__', lambda a, b: None)
    validator = get_validator(release_notes)
    assert validator.is_file_valid() == expected_result
