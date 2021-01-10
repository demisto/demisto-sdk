import pytest
from demisto_sdk.commands.common.content.objects.pack_objects import \
    IndicatorField
from demisto_sdk.commands.common.content.objects.pack_objects.indicator_field.indicator_field import \
    GroupFieldTypes
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import \
    INDICATOR_FIELD

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'


def mock_indicator_field(repo, indicator_field_data=None):
    pack = repo.create_pack('Temp')
    return pack.create_incident_field(name='MyIndicatorField', content=indicator_field_data if indicator_field_data
                                      else INDICATOR_FIELD)


def test_prefix(repo):
    indicator_field = mock_indicator_field(repo)
    obj = IndicatorField(indicator_field.path)
    assert obj.normalize_file_name() == "incidentfield-indicatorfield-MyIndicatorField.json"


NAME_SANITY_FILE = {
    'cliName': 'sanityname',
    'name': 'sanity name',
    'id': 'incident',
    'content': True,
}

BAD_NAME_1 = {
    'cliName': 'sanityname',
    'name': 'Incident',
    'content': True,
}

BAD_NAME_2 = {
    'cliName': 'sanityname',
    'name': 'case',
    'content': True,
}

BAD_NAME_3 = {
    'cliName': 'sanityname',
    'name': 'Playbook',
    'content': True,
}

GOOD_NAME_4 = {
    'cliName': 'sanityname',
    'name': 'Alerting feature',
    'content': True,
}

BAD_NAME_5 = {
    'cliName': 'sanity name',
    'name': 'INciDeNts',
    'content': True,
}

INPUTS_NAMES = [
    (NAME_SANITY_FILE, False),
    (BAD_NAME_1, True),
    (BAD_NAME_2, True),
    (BAD_NAME_3, True),
    (GOOD_NAME_4, False),
    (BAD_NAME_5, True)
]


@pytest.mark.parametrize('current_file, answer', INPUTS_NAMES)
def test_is_valid_name_sanity(current_file, answer, repo, capsys):
    incident_field_data = INDICATOR_FIELD.copy()
    for key, val in current_file.items():
        incident_field_data[key] = val
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    incident_field_obj.is_valid_name()
    output, _ = capsys.readouterr()
    assert ('IF100' in str(output)) is answer


CONTENT_1 = {
    'content': True
}

CONTENT_BAD_1 = {
    'content': False
}

INPUTS_FLAGS = [
    (CONTENT_1, True),
    (CONTENT_BAD_1, False),
]


@pytest.mark.parametrize('current_file, answer', INPUTS_FLAGS)
def test_is_valid_content_flag_sanity(current_file, answer, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    for key, val in current_file.items():
        incident_field_data[key] = val
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_valid_content_flag() is answer


def test_is_valid_content_flag_sanity_no_content_flag(repo):
    incident_field_data = INDICATOR_FIELD.copy()
    del incident_field_data['content']
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_valid_content_flag() is False


SYSTEM_FLAG_1 = {
    'system': False,
    'content': True,
}

SYSTEM_FLAG_BAD_1 = {
    'system': True,
    'content': True,
}

INPUTS_SYSTEM_FLAGS = [
    (SYSTEM_FLAG_1, True),
    (SYSTEM_FLAG_BAD_1, False)
]


@pytest.mark.parametrize('current_file, answer', INPUTS_SYSTEM_FLAGS)
def test_is_valid_system_flag_sanity(current_file, answer, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    for key, val in current_file.items():
        incident_field_data[key] = val
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_valid_system_flag() is answer


VALID_CLINAMES_AND_GROUPS = [
    ("validind", GroupFieldTypes.INDICATOR_FIELD),
    ("validind", GroupFieldTypes.EVIDENCE_FIELD),
    ("validind", GroupFieldTypes.INDICATOR_FIELD)
]


@pytest.mark.parametrize("cliname, group", VALID_CLINAMES_AND_GROUPS)
def test_is_cliname_is_builtin_key(cliname, group, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['cliName'] = cliname
    incident_field_data['group'] = group
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_cliname_is_builtin_key()


INVALID_CLINAMES_AND_GROUPS = [
    ("id", GroupFieldTypes.INDICATOR_FIELD),
    ("id", GroupFieldTypes.EVIDENCE_FIELD),
    ("id", GroupFieldTypes.INDICATOR_FIELD)
]


@pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
def test_is_cliname_is_builtin_key_invalid(cliname, group, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['cliName'] = cliname
    incident_field_data['group'] = group
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert not incident_field_obj.is_cliname_is_builtin_key()


VALID_CLINAMES = [
    "agoodid",
    "anot3erg00did",
]


@pytest.mark.parametrize("cliname", VALID_CLINAMES)
def test_matching_cliname_regex(cliname, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['cliName'] = cliname
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_matching_cliname_regex()


INVALID_CLINAMES = [
    "invalid cli",
    "invalid_cli",
    "invalid$$cli",
    "לאסליטוב",
]


@pytest.mark.parametrize("cliname", INVALID_CLINAMES)
def test_matching_cliname_regex_invalid(cliname, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['cliName'] = cliname
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert not incident_field_obj.is_matching_cliname_regex()


@pytest.mark.parametrize("cliname, group", VALID_CLINAMES_AND_GROUPS)
def test_is_valid_cliname(cliname, group, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['cliName'] = cliname
    incident_field_data['group'] = group
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_valid_cliname()


@pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
def test_is_valid_cliname_invalid(cliname, group, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['cliName'] = cliname
    incident_field_data['group'] = group
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert not incident_field_obj.is_valid_cliname()


data_is_valid_version = [
    (-1, True),
    (0, False),
    (1, False),
]


@pytest.mark.parametrize('version, is_valid', data_is_valid_version)
def test_is_valid_version(version, is_valid, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['version'] = version
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'


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
    old_file = INDICATOR_FIELD.copy()
    if old_from_version:
        old_file['fromVersion'] = old_from_version
    else:
        del old_file['fromVersion']

    incident_field_data = INDICATOR_FIELD.copy()
    if current_from_version:
        incident_field_data['fromVersion'] = current_from_version
    else:
        del incident_field_data['fromVersion']

    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_changed_from_version(old_file) is answer


data_required = [
    (True, False),
    (False, True),
]


@pytest.mark.parametrize('required, is_valid', data_required)
def test_is_valid_required(required, is_valid, repo):
    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['required'] = required
    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_valid_required() == is_valid, f'is_valid_required({required})' \
                                                               f' returns {not is_valid}.'


data_is_changed_type = [
    ('shortText', 'shortText', False),
    ('shortText', 'longText', True),
    ('number', 'number', False),
    ('shortText', 'number', True),
    ('timer', 'timer', False),
    ('timer', 'number', True),
    ('timer', 'shortText', True),
    ('singleSelect', 'singleSelect', False),
    ('singleSelect', 'shortText', True)
]


@pytest.mark.parametrize('current_type, old_type, is_valid', data_is_changed_type)
def test_is_changed_type(current_type, old_type, is_valid, repo):
    old_file = INDICATOR_FIELD.copy()
    old_file['type'] = old_type

    incident_field_data = INDICATOR_FIELD.copy()
    incident_field_data['type'] = current_type

    incident_field = mock_indicator_field(repo, incident_field_data)
    incident_field_obj = IndicatorField(incident_field.path)
    assert incident_field_obj.is_changed_type(old_file) == is_valid, f'is_changed_type({current_type}, {old_type})' \
                                                                     f' returns {not is_valid}.'
