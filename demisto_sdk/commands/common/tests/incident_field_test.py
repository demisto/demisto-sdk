import pytest

from demisto_sdk.commands.common.hook_validations.incident_field import IncidentFieldValidator, GroupFieldTypes
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
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
