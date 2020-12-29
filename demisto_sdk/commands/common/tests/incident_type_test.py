from typing import Optional

import pytest
from demisto_sdk.commands.common.hook_validations.incident_type import \
    IncidentTypeValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from mock import patch


def mock_structure(file_path=None, current_file=None, old_file=None):
    # type: (Optional[str], Optional[dict], Optional[dict]) -> StructureValidator
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'incident_type'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = 'master'
        structure.branch_name = ''
        return structure


data_is_valid_version = [
    (-1, True),
    (0, False),
    (1, False),
]


@pytest.mark.parametrize('version, is_valid', data_is_valid_version)
def test_is_valid_version(version, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"version": version}
    validator = IncidentTypeValidator(structure)
    assert validator.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'


data_is_id_equal_name = [
    ('AWS EC2 Instance Misconfiguration', 'AWS EC2 Instance Misconfiguration', True),
    ('AWS EC2 Instance Misconfiguration', 'AWS EC2 Instance Wrong configuration', False)
]


@pytest.mark.parametrize('id_, name, is_valid', data_is_id_equal_name)
def test_is_id_equal_name(id_, name, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"id": id_, "name": name}
    validator = IncidentTypeValidator(structure)
    assert validator.is_id_equals_name() == is_valid, f'is_id_equal_name returns {not is_valid}.'


data_is_including_int_fields = [
    ({"fromVersion": "5.0.0", "hours": 1, "days": 2, "weeks": 3, "hoursR": 1, "daysR": 2, "weeksR": 3}, True),
    ({"fromVersion": "5.0.0", "hours": 1, "days": 2, "weeks": "3", "hoursR": 1, "daysR": 2, "weeksR": 3}, False),
    ({"fromVersion": "5.0.0", "hours": 1, "days": 2, "weeks": 3, "hoursR": 1, "daysR": 2}, False),
]


@pytest.mark.parametrize('current_file, is_valid', data_is_including_int_fields)
def test_is_including_fields(current_file, is_valid):
    structure = mock_structure("", current_file)
    validator = IncidentTypeValidator(structure)
    assert validator.is_including_int_fields() == is_valid, f'is_including_int_fields returns {not is_valid}.'


IS_FROM_VERSION_CHANGED_NO_OLD = {}  # type: dict[any, any]
IS_FROM_VERSION_CHANGED_OLD = {"fromVersion": "5.0.0"}
IS_FROM_VERSION_CHANGED_NEW = {"fromVersion": "5.0.0"}
IS_FROM_VERSION_CHANGED_NO_NEW = {}  # type: dict[any, any]
IS_FROM_VERSION_CHANGED_NEW_HIGHER = {"fromVersion": "5.5.0"}
IS_CHANGED_FROM_VERSION_INPUTS = [
    (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_OLD, False),
    (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NEW, True),
    (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW, False),
    (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_NEW, False),
    (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW_HIGHER, True),
]


@pytest.mark.parametrize("current_from_version, old_from_version, answer", IS_CHANGED_FROM_VERSION_INPUTS)
def test_is_changed_from_version(current_from_version, old_from_version, answer):
    structure = StructureValidator("")
    structure.old_file = old_from_version
    structure.current_file = current_from_version
    validator = IncidentTypeValidator(structure)
    assert validator.is_changed_from_version() is answer


IS_VALID_PLAYBOOK_ID = [
    ('valid playbook', True),
    ('', True),
    ('12b3a41b-04ce-4417-89b3-4efd95d28012', False),
    ('abbababb-aaaa-bbbb-cccc-abcdabcdabcd', False)
]


@pytest.mark.parametrize("playbook_id, is_valid", IS_VALID_PLAYBOOK_ID)
def test_is_valid_playbook_id(playbook_id, is_valid):
    structure = StructureValidator("")
    structure.current_file = {"playbookId": playbook_id}
    validator = IncidentTypeValidator(structure)
    assert validator.is_valid_playbook_id() == is_valid


def test_is_valid_autoextract_no_extract_rules():
    """
    Given
    - an incident type without auto extract section .

    When
    - Running is_valid_autoextract on it.

    Then
    - Ensure returns True.
    """
    structure = StructureValidator("")
    validator = IncidentTypeValidator(structure)
    assert validator.is_valid_autoextract()


EXTRACT_VARIATIONS = [
    ({"extractAsIsIndicatorTypeId": "", "isExtractingAllIndicatorTypes": False, "extractIndicatorTypesIDs": []}, True),
    ({"extractAsIsIndicatorTypeId": "IP", "isExtractingAllIndicatorTypes": False, "extractIndicatorTypesIDs": []}, True),
    ({"extractAsIsIndicatorTypeId": "", "isExtractingAllIndicatorTypes": False,
      "extractIndicatorTypesIDs": ["IP", "CIDR"]}, True),
    ({"extractAsIsIndicatorTypeId": "", "isExtractingAllIndicatorTypes": True, "extractIndicatorTypesIDs": []}, True),
    ({"extractAsIsIndicatorTypeId": "IP", "isExtractingAllIndicatorTypes": False,
      "extractIndicatorTypesIDs": ["IP"]}, False),
    ({"extractAsIsIndicatorTypeId": "IP", "isExtractingAllIndicatorTypes": True,
      "extractIndicatorTypesIDs": []}, False),
    ({"extractAsIsIndicatorTypeId": "", "isExtractingAllIndicatorTypes": True,
      "extractIndicatorTypesIDs": ["IP"]}, False),
    ({"extractAsIsIndicatorTypeId": "IP", "isExtractingAllIndicatorTypes": True,
      "extractIndicatorTypesIDs": ["IP"]}, False),
    ({}, False)
]


@pytest.mark.parametrize("extract_field, answer", EXTRACT_VARIATIONS)
def test_is_valid_autoextract_fields(extract_field, answer):
    """
    Given
    - an incident type with a valid or invalid auto extract section .

    When
    - Running is_valid_autoextract on it.

    Then
    - Ensure returns True if the field is formatted correctly and False otherwise.
    """
    structure = StructureValidator("")
    validator = IncidentTypeValidator(structure)
    validator.current_file['extractSettings'] = {
        'mode': "All",
        'fieldCliNameToExtractSettings': {
            "incident_field": extract_field
        }
    }
    assert validator.is_valid_autoextract() is answer


EXTRACTION_MODE_VARIATIONS = [
    ('All', True),
    ('Specific', True),
    (None, False),
    ('', False),
    ('all', False)
]


@pytest.mark.parametrize("extract_mode, answer", EXTRACTION_MODE_VARIATIONS)
def test_is_valid_autoextract_mode(extract_mode, answer):
    """
    Given
    - an incident type with a valid or invalid auto extract mode.

    When
    - Running is_valid_autoextract on it.

    Then
    - Ensure returns True if the field is formatted correctly and False otherwise.
    """
    structure = StructureValidator("")
    validator = IncidentTypeValidator(structure)
    validator.current_file['extractSettings'] = {
        'mode': extract_mode,
        'fieldCliNameToExtractSettings': {
            "incident_field": {
                "extractAsIsIndicatorTypeId": "",
                "isExtractingAllIndicatorTypes": False,
                "extractIndicatorTypesIDs": []
            }
        }
    }
    assert validator.is_valid_autoextract() is answer
