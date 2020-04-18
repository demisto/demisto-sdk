import pytest
from demisto_sdk.commands.common.hook_validations.incident_field import (
    GroupFieldTypes, IncidentFieldValidator)
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from mock import patch


class TestIncidentFieldsValidator:
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
        (NAME_SANITY_FILE, True),
        (BAD_NAME_1, False),
        (BAD_NAME_2, False),
        (BAD_NAME_3, False),
        (GOOD_NAME_4, True),
        (BAD_NAME_5, False)
    ]

    @pytest.mark.parametrize('current_file, answer', INPUTS_NAMES)
    def test_is_valid_name_sanity(self, current_file, answer):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert validator.is_valid_name() is answer

    CONTENT_1 = {
        'content': True
    }

    CONTENT_BAD_1 = {
        'content': False
    }

    CONTENT_BAD_2 = {
        'something': True
    }

    INPUTS_FLAGS = [
        (CONTENT_1, True),
        (CONTENT_BAD_1, False),
        (CONTENT_BAD_2, False)
    ]

    @pytest.mark.parametrize('current_file, answer', INPUTS_FLAGS)
    def test_is_valid_content_flag_sanity(self, current_file, answer):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert validator.is_valid_content_flag() is answer

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
    def test_is_valid_system_flag_sanity(self, current_file, answer):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert validator.is_valid_system_flag() is answer

    VALID_CLINAMES_AND_GROUPS = [
        ("validind", GroupFieldTypes.INCIDENT_FIELD),
        ("validind", GroupFieldTypes.EVIDENCE_FIELD),
        ("validind", GroupFieldTypes.INDICATOR_FIELD)
    ]

    @pytest.mark.parametrize("cliname, group", VALID_CLINAMES_AND_GROUPS)
    def test_is_cliname_is_builtin_key(self, cliname, group):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            current_file = {"cliName": cliname, "group": group}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert validator.is_cliname_is_builtin_key()

    INVALID_CLINAMES_AND_GROUPS = [
        ("id", GroupFieldTypes.INCIDENT_FIELD),
        ("id", GroupFieldTypes.EVIDENCE_FIELD),
        ("id", GroupFieldTypes.INDICATOR_FIELD)
    ]

    @pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
    def test_is_cliname_is_builtin_key_invalid(self, cliname, group):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            current_file = {"cliName": cliname, "group": group}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert not validator.is_cliname_is_builtin_key()

    VALID_CLINAMES = [
        "agoodid",
        "anot3erg00did",
    ]

    @pytest.mark.parametrize("cliname", VALID_CLINAMES)
    def test_matching_cliname_regex(self, cliname):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            current_file = {"cliName": cliname}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert validator.is_matching_cliname_regex()

    INVALID_CLINAMES = [
        "invalid cli",
        "invalid_cli",
        "invalid$$cli",
        "לאסליטוב",
    ]

    @pytest.mark.parametrize("cliname", INVALID_CLINAMES)
    def test_matching_cliname_regex_invalid(self, cliname):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            current_file = {"cliName": cliname}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert not validator.is_matching_cliname_regex()

    @pytest.mark.parametrize("cliname, group", VALID_CLINAMES_AND_GROUPS)
    def test_is_valid_cliname(self, cliname, group):
        current_file = {"cliName": cliname, "group": group}
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert validator.is_valid_cliname()

    @pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
    def test_is_valid_cliname_invalid(self, cliname, group):
        current_file = {"cliName": cliname, "group": group}
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            validator = IncidentFieldValidator(structure)
            validator.current_file = current_file
            assert not validator.is_valid_cliname()

    data_is_valid_version = [
        (-1, True),
        (0, False),
        (1, False),
    ]

    @pytest.mark.parametrize('version, is_valid', data_is_valid_version)
    def test_is_valid_version(self, version, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"version": version}
        validator = IncidentFieldValidator(structure)
        assert validator.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'

    data_is_valid_from_version = [
        ('5.0.0', True),
        ('4.', False),
        ('', False),
        ('4.0.0', False),
        ('5.0.1', True),
        ('100.0.0', True),
        ('5', False),
        (None, False)
    ]

    @pytest.mark.parametrize('from_version, is_valid', data_is_valid_from_version)
    def test_is_current_valid_from_version(self, from_version, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"fromVersion": from_version}
        validator = IncidentFieldValidator(structure)
        assert validator.is_current_valid_from_version() == is_valid, f'is_valid_from_version({from_version})' \
                                                                      f' returns {not is_valid}.'

    IS_FROM_VERSION_CHANGED_NO_OLD = {}
    IS_FROM_VERSION_CHANGED_OLD = {"fromVersion": "5.0.0"}
    IS_FROM_VERSION_CHANGED_NEW = {"fromVersion": "5.0.0"}
    IS_FROM_VERSION_CHANGED_NO_NEW = {}
    IS_FROM_VERSION_CHANGED_NEW_HIGHER = {"fromVersion": "5.5.0"}
    IS_CHANGED_FROM_VERSION_INPUTS = [
        (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_OLD, False),
        (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NEW, True),
        (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW, False),
        (IS_FROM_VERSION_CHANGED_NO_OLD, IS_FROM_VERSION_CHANGED_NO_NEW, False),
        (IS_FROM_VERSION_CHANGED_OLD, IS_FROM_VERSION_CHANGED_NEW_HIGHER, True),
    ]

    @pytest.mark.parametrize("current_from_version, old_from_version, answer", IS_CHANGED_FROM_VERSION_INPUTS)
    def test_is_changed_from_version(self, current_from_version, old_from_version, answer):
        structure = StructureValidator("")
        structure.old_file = old_from_version
        structure.current_file = current_from_version
        validator = IncidentFieldValidator(structure)
        assert validator.is_changed_from_version() is answer

    data_required = [
        (True, False),
        (False, True),
    ]

    @pytest.mark.parametrize('required, is_valid', data_required)
    def test_is_valid_required(self, required, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"required": required}
        validator = IncidentFieldValidator(structure)
        assert validator.is_valid_required() == is_valid, f'is_valid_required({required})' \
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
    def test_is_changed_type(self, current_type, old_type, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"type": current_type}
        structure.old_file = {"type": old_type}
        validator = IncidentFieldValidator(structure)
        assert validator.is_changed_type() == is_valid, f'is_changed_type({current_type}, {old_type})' \
                                                        f' returns {not is_valid}.'
