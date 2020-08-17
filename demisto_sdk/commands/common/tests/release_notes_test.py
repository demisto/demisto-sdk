import os

import pytest
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.release_notes import \
    ReleaseNotesValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator


def get_validator(file_path='', modified_files=None, added_files=None):
    release_notes_validator = ReleaseNotesValidator("")
    release_notes_validator.file_path = os.path.join(FILES_PATH, 'CortexXDR')
    release_notes_validator.release_notes_path = file_path
    release_notes_validator.latest_release_notes = file_path
    release_notes_validator.modified_files = modified_files
    release_notes_validator.added_files = added_files
    release_notes_validator.pack_name = 'CortexXDR'
    release_notes_validator.ignored_errors = {}
    release_notes_validator.checked_files = set()
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
    ReleaseNotesValidator.ignored_errors = []
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


NOT_FILLED_OUT_RN = '''
### Incident Types
#### Cortex XDR Incident
- %%UPDATE_RN%%

### Incident Fields
#### XDR Alerts
- %%UPDATE_RN%%

### Integrations
#### Palo Alto Networks Cortex XDR - Investigation and Response
- %%UPDATE_RN%%

### Scripts
#### EntryWidgetNumberHostsXDR
- %%UPDATE_RN%%
'''
FILLED_OUT_RN = '''
### Incident Types
#### Cortex XDR Incident
- Test

### Incident Fields
#### XDR Alerts
- Test

### Integrations
#### Palo Alto Networks Cortex XDR - Investigation and Response
- Test

### Scripts
#### EntryWidgetNumberHostsXDR
- Test

### Playbooks
#### Cortex XDR Incident Handling
- test
'''


TEST_RELEASE_NOTES_TEST_BANK_1 = [
    ('', False),  # Completely Empty
    ('### Integrations\n#### HelloWorld\n- Grammar correction for code '  # Missing Items
     'description.\n\n### Scripts\n#### HelloWorldScript \n- Grammar correction for '
     'code description. ', False),
    (NOT_FILLED_OUT_RN, True),
    (FILLED_OUT_RN, True)

]
MODIFIED_FILES = [
    os.path.join(FILES_PATH, 'CortexXDR', 'Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml'),
    os.path.join(FILES_PATH, 'CortexXDR', 'IncidentTypes/Cortex_XDR_Incident.json'),
    os.path.join(FILES_PATH, 'CortexXDR', 'IncidentFields/XDR_Alerts.json'),
    os.path.join(FILES_PATH, 'CortexXDR', 'Scripts/EntryWidgetNumberHostsXDR/EntryWidgetNumberHostsXDR.yml'),
    os.path.join(FILES_PATH, 'CortexXDR', 'README.md'),
]
ADDED_FILES = [
    os.path.join(FILES_PATH, 'CortexXDR', 'Playbooks/Cortex_XDR_Incident_Handling.yml'),
    os.path.join(FILES_PATH, 'CortexXDR', 'ReleaseNotes/1_0_0.md'),
    os.path.join(FILES_PATH, 'CortexXDR', 'README.md'),
]


@pytest.mark.parametrize('release_notes, complete_expected_result', TEST_RELEASE_NOTES_TEST_BANK_1)
def test_are_release_notes_complete(release_notes, complete_expected_result, mocker):
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
    mocker.patch.object(StructureValidator, 'scheme_of_file_by_path', return_value='integration')
    validator = get_validator(release_notes, MODIFIED_FILES)
    assert validator.are_release_notes_complete() == complete_expected_result


MODIFIED_FILES_INVALID = [
    os.path.join(FILES_PATH, 'CortexXDR', 'Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml'),
    os.path.join(FILES_PATH, 'CortexXDR', 'IncidentTypes/Cortex_XDR_Incident.json'),
    os.path.join(FILES_PATH, 'CortexXDR', 'IncidentFields/XDR_Alerts.json'),
    os.path.join(FILES_PATH, 'CortexXDR', 'Scripts/EntryWidgetNumberHostsXDR/EntryWidgetNumberHostsXDR.yml'),
    os.path.join(FILES_PATH, 'CortexXDR', 'TestPlaybooks/Cortex_XDR.yml'),
    os.path.join(FILES_PATH, 'CortexXDR', '.secrets-ignore'),
]


@pytest.mark.parametrize('release_notes, complete_expected_result', TEST_RELEASE_NOTES_TEST_BANK_1)
def test_are_release_notes_complete_invalid_file_type(release_notes, complete_expected_result, mocker):
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
    mocker.patch.object(StructureValidator, 'scheme_of_file_by_path', return_value='integration')
    validator = get_validator(release_notes, MODIFIED_FILES_INVALID)
    assert validator.are_release_notes_complete() == complete_expected_result


TEST_RELEASE_NOTES_TEST_BANK_ADDED = [
    ('', False),  # Completely Empty
    ('### Integrations\n#### HelloWorld\n- Grammar correction for code '  # Missing Items
     'description.\n\n### Scripts\n#### HelloWorldScript\n- Grammar correction for '
     'code description. ', False),
    (NOT_FILLED_OUT_RN, False),
    (FILLED_OUT_RN, True)

]


@pytest.mark.parametrize('release_notes, complete_expected_result', TEST_RELEASE_NOTES_TEST_BANK_ADDED)
def test_are_release_notes_complete_added(release_notes, complete_expected_result, mocker):
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
    mocker.patch.object(StructureValidator, 'scheme_of_file_by_path', return_value='integration')
    validator = get_validator(release_notes, MODIFIED_FILES, ADDED_FILES)
    assert validator.are_release_notes_complete() == complete_expected_result


TEST_RELEASE_NOTES_TEST_BANK_2 = [
    ('', False),  # Completely Empty
    ('### Integrations\n#### HelloWorld\n- Grammar correction for code '  # Missing Items
     'description.\n\n### Scripts\n#### HelloWorldScript\n- Grammar correction for '
     'code description. ', True),
    (NOT_FILLED_OUT_RN, False),
    (FILLED_OUT_RN, True),
    ('<!-- Test -->', False),
    ('<!-- Test --> #### Integrations\n##### Some Integration', True)

]


@pytest.mark.parametrize('release_notes, filled_expected_result', TEST_RELEASE_NOTES_TEST_BANK_2)
def test_has_release_notes_been_filled_out(release_notes, filled_expected_result, mocker):
    """
    Given
    - Case 1: Empty release notes.
    - Case 2: Not filled out release notes.
    - Case 3: Valid release notes
    - Case 4: Release notes with all items excluded.
    - Case 5: Release notes with exclusion, but also with filled out section.

    When
    - Running validation on release notes.

    Then
    - Ensure validation correctly identifies valid release notes.
    - Case 1: Should return the prompt "Please complete the release notes found at: {path}" and
              return True
    - Case 2: Should return the prompt "Please finish filling out the release notes found at: {path}" and
              return False
    - Case 3: Should print nothing and return True
    - Case 4: Should return the prompt "Your release notes file is empty" and return False
    - Case 5: Should print nothing and return True
    """
    mocker.patch.object(ReleaseNotesValidator, '__init__', lambda a, b: None)
    mocker.patch.object(StructureValidator, 'scheme_of_file_by_path', return_value='integration')
    validator = get_validator(release_notes, MODIFIED_FILES)
    assert validator.has_release_notes_been_filled_out() == filled_expected_result
