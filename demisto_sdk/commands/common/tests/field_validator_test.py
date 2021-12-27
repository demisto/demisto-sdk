import pytest
from mock import patch

from demisto_sdk.commands.common.hook_validations.field_base_validator import (
    FieldBaseValidator, GroupFieldTypes)
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator


class TestFieldValidator:
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
    def test_is_valid_name_sanity(self, current_file, answer):
        import os
        import sys
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file

            with open("file", 'w') as temp_out:
                old_stdout = sys.stdout
                sys.stdout = temp_out
                validator.is_valid_name()
                sys.stdout = old_stdout

            with open('file', 'r') as temp_out:
                output = temp_out.read()
                assert ('IF100' in str(output)) is answer
            # remove the temp file
            os.system('rm -rf file')

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
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
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
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
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
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_cli_name_is_builtin_key()

    INVALID_CLINAMES_AND_GROUPS = [
        ("id", GroupFieldTypes.INCIDENT_FIELD),
        ("id", GroupFieldTypes.EVIDENCE_FIELD),
        ("id", GroupFieldTypes.INDICATOR_FIELD)
    ]

    @pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
    def test_is_cli_name_is_builtin_key_invalid(self, cliname, group):
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            current_file = {"cliName": cliname, "group": group}
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), {'id'})
            validator.current_file = current_file
            assert not validator.is_cli_name_is_builtin_key()

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
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_matching_cli_name_regex()

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
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert not validator.is_matching_cli_name_regex()

    @pytest.mark.parametrize("cliname, group", VALID_CLINAMES_AND_GROUPS)
    def test_is_valid_cliname(self, cliname, group):
        current_file = {"cliName": cliname, "group": group}
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            assert validator.is_valid_cli_name()

    @pytest.mark.parametrize("cliname, group", INVALID_CLINAMES_AND_GROUPS)
    def test_is_valid_cli_name_invalid(self, cliname, group):
        current_file = {"cliName": cliname, "group": group}
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), {'id'})
            validator.current_file = current_file
            assert not validator.is_valid_cli_name()

    data_is_valid_version = [
        (-1, True),
        (0, False),
        (1, False),
    ]

    @pytest.mark.parametrize('version, is_valid', data_is_valid_version)
    def test_is_valid_version(self, version, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"version": version}
        validator = FieldBaseValidator(structure, set(), set())
        assert validator.is_valid_version() == is_valid, f'is_valid_version({version}) returns {not is_valid}.'

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
    def test_is_changed_from_version(self, current_from_version, old_from_version, answer):
        structure = StructureValidator("")
        structure.old_file = old_from_version
        structure.current_file = current_from_version
        validator = FieldBaseValidator(structure, set(), set())
        assert validator.is_changed_from_version() is answer
        structure.quite_bc = True
        assert validator.is_changed_from_version() is False

    data_required = [
        (True, False),
        (False, True),
    ]

    @pytest.mark.parametrize('required, is_valid', data_required)
    def test_is_valid_required(self, required, is_valid):
        structure = StructureValidator("")
        structure.current_file = {"required": required}
        validator = FieldBaseValidator(structure, set(), set())
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
        validator = FieldBaseValidator(structure, set(), set())
        assert validator.is_changed_type() == is_valid, f'is_changed_type({current_type}, {old_type})' \
                                                        f' returns {not is_valid}.'
        structure.quite_bc = True
        assert validator.is_changed_type() is False

    FIELD_NAME1 = {
        'name': 'pack name field',
    }
    FIELD_NAME2 = {
        'name': 'pack prefix field',
    }
    FIELD_NAME3 = {
        'name': 'field',
    }
    PACK_METADATA1 = {'name': 'pack name', 'itemPrefix': ['pack prefix']}
    PACK_METADATA2 = {'name': 'pack name'}

    INPUTS_NAMES2 = [
        (FIELD_NAME1, PACK_METADATA1, False),
        (FIELD_NAME1, PACK_METADATA2, True),
        (FIELD_NAME2, PACK_METADATA1, True),
        (FIELD_NAME2, PACK_METADATA2, False),
        (FIELD_NAME3, PACK_METADATA1, False)
    ]

    @pytest.mark.parametrize('current_file,pack_metadata, answer', INPUTS_NAMES2)
    def test_is_valid_name_prefix(self, current_file, pack_metadata, answer, mocker):
        """
            Given
            - A set of indicator fields

            When
            - Running is_valid_incident_field_name_prefix on it.

            Then
            - Ensure validate fails when the field name does not start with the pack name prefix.
        """
        from demisto_sdk.commands.common.hook_validations import \
            field_base_validator
        with patch.object(StructureValidator, '__init__', lambda a, b: None):
            structure = StructureValidator("")
            structure.current_file = current_file
            structure.old_file = None
            structure.file_path = "random_path"
            structure.is_valid = True
            structure.prev_ver = 'master'
            structure.branch_name = ''
            validator = FieldBaseValidator(structure, set(), set())
            validator.current_file = current_file
            mocker.patch.object(field_base_validator, 'get_pack_metadata', return_value=pack_metadata)
            assert validator.is_valid_field_name_prefix() == answer

    # def test_indicator_field_not_html_type(self, pack):
    #     indicator_field = pack.create_indicator_field('HTMLIndicatorInvalid', {'type': 'html'})
    #     structure = StructureValidator(indicator_field.path)
    #     validator = FieldBaseValidator(structure, set(), set())
    #     assert not validator.is_valid_type()
