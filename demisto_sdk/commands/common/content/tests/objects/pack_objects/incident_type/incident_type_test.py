import pytest
from demisto_sdk.commands.common.content.objects.pack_objects import \
    IncidentType
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import \
    INCIDENT_TYPE

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'


def mock_incident_type(repo, incident_type_data=None):
    pack = repo.create_pack('Temp')
    return pack.create_incident_type(name='MyIncidentType', content=incident_type_data if
                                     incident_type_data else INCIDENT_TYPE)


def test_objects_factory(repo):
    incident_type = mock_incident_type(repo)
    obj = path_to_pack_object(incident_type.path)
    assert isinstance(obj, IncidentType)


def test_prefix(repo):
    incident_type = mock_incident_type(repo)
    obj = IncidentType(incident_type.path)
    assert obj.normalize_file_name() == incident_type.name


data_is_valid_version = [
    (-1, True),
    (0, False),
    (1, False),
]


@pytest.mark.parametrize('version, is_valid', data_is_valid_version)
def test_is_valid_version(version, is_valid, repo):
    incident_type_data = INCIDENT_TYPE.copy()
    incident_type_data['version'] = version
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'


data_is_id_equal_name = [
    ('AWS EC2 Instance Misconfiguration', 'AWS EC2 Instance Misconfiguration', True),
    ('AWS EC2 Instance Misconfiguration', 'AWS EC2 Instance Wrong configuration', False)
]


@pytest.mark.parametrize('id_, name, is_valid', data_is_id_equal_name)
def test_is_id_equal_name(id_, name, is_valid, repo):
    incident_type_data = INCIDENT_TYPE.copy()
    incident_type_data['id'] = id_
    incident_type_data['name'] = name
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_id_equals_name() == is_valid, f'is_id_equal_name returns {not is_valid}.'


data_is_including_int_fields = [
    ({"fromVersion": "5.0.0", "hours": 1, "days": 2, "weeks": 3, "hoursR": 1, "daysR": 2, "weeksR": 3}, True),
    ({"fromVersion": "5.0.0", "hours": 1, "days": 2, "weeks": "3", "hoursR": 1, "daysR": 2, "weeksR": 3}, False),
]


@pytest.mark.parametrize('current_file, is_valid', data_is_including_int_fields)
def test_is_including_fields(current_file, is_valid, repo):
    incident_type_data = INCIDENT_TYPE.copy()
    for key, val in current_file.items():
        incident_type_data[key] = val
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_including_int_fields() == is_valid, f'is_including_int_fields returns {not is_valid}.'


def test_is_including_fields_no_weeksr(repo):
    incident_type_data = INCIDENT_TYPE.copy()
    del incident_type_data["weeksR"]
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_including_int_fields() is False


IS_FROM_VERSION_CHANGED_NO_OLD = None
IS_FROM_VERSION_CHANGED_OLD = "5.0.0"
IS_FROM_VERSION_CHANGED_NEW = "5.0.0"
IS_FROM_VERSION_CHANGED_NO_NEW = None
IS_FROM_VERSION_CHANGED_NEW_HIGHER = "5.5.0"
IS_CHANGED_FROM_VERSION_INPUTS = [
    (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_OLD, False),
    (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NEW, True),
    (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW, False),
    (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_NEW, False),
    (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW_HIGHER, True),
]


@pytest.mark.parametrize("current_from_version, old_from_version, answer", IS_CHANGED_FROM_VERSION_INPUTS)
def test_is_changed_from_version(current_from_version, old_from_version, answer, repo):
    old_file = INCIDENT_TYPE.copy()
    if old_from_version:
        old_file['fromVersion'] = old_from_version
    else:
        del old_file['fromVersion']

    incident_type_data = INCIDENT_TYPE.copy()
    if current_from_version:
        incident_type_data['fromVersion'] = current_from_version
    else:
        del incident_type_data['fromVersion']

    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_changed_from_version(old_file) is answer


IS_VALID_PLAYBOOK_ID = [
    ('valid playbook', True),
    ('', True),
    ('12b3a41b-04ce-4417-89b3-4efd95d28012', False),
    ('abbababb-aaaa-bbbb-cccc-abcdabcdabcd', False)
]


@pytest.mark.parametrize("playbook_id, is_valid", IS_VALID_PLAYBOOK_ID)
def test_is_valid_playbook_id(playbook_id, is_valid, repo):
    incident_type_data = INCIDENT_TYPE.copy()
    incident_type_data['playbookId'] = playbook_id
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_valid_playbook_id() == is_valid


def test_is_valid_autoextract_no_extract_rules(repo):
    """
    Given
    - an incident type without auto extract section .

    When
    - Running is_valid_autoextract on it.

    Then
    - Ensure returns True.
    """
    incident_type_data = INCIDENT_TYPE.copy()
    del incident_type_data['extractSettings']
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_valid_autoextract()


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
def test_is_valid_autoextract_fields(extract_field, answer, repo):
    """
    Given
    - an incident type with a valid or invalid auto extract section .

    When
    - Running is_valid_autoextract on it.

    Then
    - Ensure returns True if the field is formatted correctly and False otherwise.
    """
    incident_type_data = INCIDENT_TYPE.copy()
    incident_type_data['extractSettings'] = {
        'mode': "All",
        'fieldCliNameToExtractSettings': {
            "incident_field": extract_field
        }
    }
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_valid_autoextract() is answer


EXTRACTION_MODE_VARIATIONS = [
    ('All', True),
    ('Specific', True),
    (None, False),
    ('', False),
    ('all', False)
]


@pytest.mark.parametrize("extract_mode, answer", EXTRACTION_MODE_VARIATIONS)
def test_is_valid_autoextract_mode(extract_mode, answer, repo):
    """
    Given
    - an incident type with a valid or invalid auto extract mode.

    When
    - Running is_valid_autoextract on it.

    Then
    - Ensure returns True if the field is formatted correctly and False otherwise.
    """
    incident_type_data = INCIDENT_TYPE.copy()
    incident_type_data['extractSettings'] = {
        'mode': extract_mode,
        'fieldCliNameToExtractSettings': {
            "incident_field": {
                "extractAsIsIndicatorTypeId": "",
                "isExtractingAllIndicatorTypes": False,
                "extractIndicatorTypesIDs": []
            }
        }
    }
    incident_type = mock_incident_type(repo, incident_type_data)
    incident_type_obj = IncidentType(incident_type.path)
    assert incident_type_obj.is_valid_autoextract() is answer
