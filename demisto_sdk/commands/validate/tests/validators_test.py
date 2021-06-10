import json
import os
import sys
from io import StringIO
from shutil import copyfile
from typing import Any, Type, Union

import demisto_sdk.commands.validate.validate_manager
import pytest
from demisto_sdk.commands.common.constants import (CONF_PATH, TEST_PLAYBOOK,
                                                   FileType)
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.hook_validations.dashboard import \
    DashboardValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.incident_field import \
    IncidentFieldValidator
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.hook_validations.layout import (
    LayoutsContainerValidator, LayoutValidator)
from demisto_sdk.commands.common.hook_validations.old_release_notes import \
    OldReleaseNotesValidator
from demisto_sdk.commands.common.hook_validations.pack_unique_files import \
    PackUniqueFilesValidator
from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.hook_validations.release_notes import \
    ReleaseNotesValidator
from demisto_sdk.commands.common.hook_validations.reputation import \
    ReputationValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from demisto_sdk.tests.constants_test import (
    CONF_JSON_MOCK_PATH, DASHBOARD_TARGET, DIR_LIST, IGNORED_PNG,
    INCIDENT_FIELD_TARGET, INCIDENT_TYPE_TARGET, INDICATOR_TYPE_TARGET,
    INTEGRATION_RELEASE_NOTES_TARGET, INTEGRATION_TARGET,
    INVALID_BETA_INTEGRATION, INVALID_DASHBOARD_PATH,
    INVALID_IGNORED_UNIFIED_INTEGRATION, INVALID_INCIDENT_FIELD_PATH,
    INVALID_INTEGRATION_ID_PATH, INVALID_INTEGRATION_NO_TESTS,
    INVALID_INTEGRATION_NON_CONFIGURED_TESTS, INVALID_LAYOUT_CONTAINER_PATH,
    INVALID_LAYOUT_PATH, INVALID_MULTI_LINE_1_CHANGELOG_PATH,
    INVALID_MULTI_LINE_2_CHANGELOG_PATH, INVALID_ONE_LINE_1_CHANGELOG_PATH,
    INVALID_ONE_LINE_2_CHANGELOG_PATH, INVALID_ONE_LINE_LIST_1_CHANGELOG_PATH,
    INVALID_ONE_LINE_LIST_2_CHANGELOG_PATH, INVALID_PLAYBOOK_CONDITION_1,
    INVALID_PLAYBOOK_CONDITION_2, INVALID_PLAYBOOK_ID_PATH,
    INVALID_PLAYBOOK_PATH, INVALID_PLAYBOOK_PATH_FROM_ROOT,
    INVALID_REPUTATION_PATH, INVALID_SCRIPT_PATH, INVALID_WIDGET_PATH,
    LAYOUT_TARGET, LAYOUTS_CONTAINER_TARGET, PLAYBOOK_TARGET,
    SCRIPT_RELEASE_NOTES_TARGET, SCRIPT_TARGET, VALID_BETA_INTEGRATION,
    VALID_BETA_PLAYBOOK_PATH, VALID_DASHBOARD_PATH, VALID_INCIDENT_FIELD_PATH,
    VALID_INCIDENT_TYPE_PATH, VALID_INDICATOR_FIELD_PATH,
    VALID_INTEGRATION_ID_PATH, VALID_INTEGRATION_TEST_PATH,
    VALID_LAYOUT_CONTAINER_PATH, VALID_LAYOUT_PATH, VALID_MD,
    VALID_MULTI_LINE_CHANGELOG_PATH, VALID_MULTI_LINE_LIST_CHANGELOG_PATH,
    VALID_ONE_LINE_CHANGELOG_PATH, VALID_ONE_LINE_LIST_CHANGELOG_PATH,
    VALID_PACK, VALID_PLAYBOOK_CONDITION, VALID_REPUTATION_PATH,
    VALID_SCRIPT_PATH, VALID_TEST_PLAYBOOK_PATH, VALID_WIDGET_PATH,
    WIDGET_TARGET, INVALID_TEST_PLAYBOOK_NO_DEFAULT_VERSION)
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import \
    INCIDENT_FIELD
from mock import patch
from TestSuite.test_tools import ChangeCWD


class TestValidators:
    CREATED_DIRS = list()  # type: list[str]

    @classmethod
    def setup_class(cls):
        for dir_to_create in DIR_LIST:
            if not os.path.exists(dir_to_create):
                cls.CREATED_DIRS.append(dir_to_create)
                os.makedirs(dir_to_create)
        copyfile(CONF_JSON_MOCK_PATH, CONF_PATH)

    @classmethod
    def teardown_class(cls):
        os.remove(CONF_PATH)
        for dir_to_delete in cls.CREATED_DIRS:
            if os.path.exists(dir_to_delete):
                os.rmdir(dir_to_delete)

    INPUTS_IS_VALID_VERSION = [
        (VALID_LAYOUT_PATH, LAYOUT_TARGET, True, LayoutValidator),
        (INVALID_LAYOUT_PATH, LAYOUT_TARGET, False, LayoutValidator),
        (VALID_LAYOUT_CONTAINER_PATH, LAYOUTS_CONTAINER_TARGET, True, LayoutsContainerValidator),
        (INVALID_LAYOUT_CONTAINER_PATH, LAYOUTS_CONTAINER_TARGET, False, LayoutsContainerValidator),
        (VALID_WIDGET_PATH, WIDGET_TARGET, True, WidgetValidator),
        (INVALID_WIDGET_PATH, WIDGET_TARGET, False, WidgetValidator),
        (VALID_DASHBOARD_PATH, DASHBOARD_TARGET, True, DashboardValidator),
        (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
        (VALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, True, IncidentFieldValidator),
        (INVALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, False, IncidentFieldValidator),
        (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, True, ScriptValidator),
        (INVALID_SCRIPT_PATH, SCRIPT_TARGET, False, ScriptValidator),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, True, PlaybookValidator),
        (INVALID_PLAYBOOK_PATH, PLAYBOOK_TARGET, False, PlaybookValidator)
    ]

    def test_validation_of_beta_playbooks(self, mocker):
        """
        Given
        - A beta playbook with 'beta: true in it's root

        When
        - Running validation on it with PlaybookValidator

        Then
        -  Ensure it accepts the 'beta' key as valid
        """
        try:
            mocker.patch.object(OldReleaseNotesValidator, 'get_master_diff', return_value='Comment.')
            copyfile(VALID_BETA_PLAYBOOK_PATH, PLAYBOOK_TARGET)
            structure = StructureValidator(VALID_BETA_PLAYBOOK_PATH, predefined_scheme='playbook')
            validator = PlaybookValidator(structure)
            mocker.patch.object(validator, 'is_script_id_valid', return_value=True)
            assert validator.is_valid_playbook(validate_rn=False)
        finally:
            os.remove(PLAYBOOK_TARGET)

    @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_VALID_VERSION)
    def test_is_valid_version(self, source, target, answer, validator):
        # type: (str, str, Any, Type[ContentEntityValidator]) -> None
        """
        Given
        - A file with either a valid or invalid version

        When
        - Running is_valid_version

        Then
        -  Ensure returns the expected results
        """
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            res_validator = validator(structure)
            assert res_validator.is_valid_version() is answer
        finally:
            os.remove(target)

    @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_VALID_VERSION)
    def test_is_valid_fromversion(self, source, target, answer, validator):
        # type: (str, str, Any, Type[ContentEntityValidator]) -> None
        """
        Given
        - A file with either a valid or invalid fromversion

        When
        - Running is_valid_fromversion

        Then
        -  Ensure returns the expected results
        """
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            res_validator = validator(structure)
            assert res_validator.is_valid_fromversion() is answer
        finally:
            os.remove(target)

    INPUTS_is_condition_branches_handled = [
        (INVALID_PLAYBOOK_CONDITION_1, False),
        (INVALID_PLAYBOOK_CONDITION_2, False),
        (VALID_PLAYBOOK_CONDITION, True)
    ]

    @pytest.mark.parametrize('source, answer', INPUTS_is_condition_branches_handled)
    def test_is_condition_branches_handled(self, source, answer):
        # type: (str, str) -> None
        try:
            copyfile(source, PLAYBOOK_TARGET)
            structure = StructureValidator(source)
            validator = PlaybookValidator(structure)
            assert validator.is_condition_branches_handled() is answer
        finally:
            os.remove(PLAYBOOK_TARGET)

    INPUTS_LOCKED_PATHS = [
        (VALID_REPUTATION_PATH, True, ReputationValidator),
        (INVALID_REPUTATION_PATH, False, ReputationValidator),
    ]

    @pytest.mark.parametrize('source, answer, validator', INPUTS_LOCKED_PATHS)
    def test_is_valid_version_locked_paths(self, source, answer, validator):
        """Tests locked path (as reputations.json) so we won't override the file"""
        structure = StructureValidator(source)
        validator = validator(structure)
        assert validator.is_valid_version() is answer

    @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_VALID_VERSION)
    def test_is_file_valid(self, source, target, answer, validator, mocker):
        # type: (str, str, Any, Type[ContentEntityValidator]) -> None
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            res_validator = validator(structure)
            mocker.patch.object(ScriptValidator, 'is_valid_script_file_path', return_value=True)
            mocker.patch.object(ScriptValidator, 'is_there_separators_in_names', return_value=True)
            assert res_validator.is_valid_file(validate_rn=False) is answer
        finally:
            os.remove(target)

    INPUTS_RELEASE_NOTES_EXISTS_VALIDATION = [
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, VALID_ONE_LINE_CHANGELOG_PATH, SCRIPT_RELEASE_NOTES_TARGET,
         OldReleaseNotesValidator, True),
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, VALID_ONE_LINE_CHANGELOG_PATH, INTEGRATION_RELEASE_NOTES_TARGET,
         OldReleaseNotesValidator, False),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET, VALID_ONE_LINE_CHANGELOG_PATH,
         INTEGRATION_RELEASE_NOTES_TARGET, OldReleaseNotesValidator, True),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET, VALID_ONE_LINE_CHANGELOG_PATH,
         SCRIPT_RELEASE_NOTES_TARGET, OldReleaseNotesValidator, False)
    ]

    @pytest.mark.parametrize('source_dummy, target_dummy, source_release_notes, target_release_notes, '
                             'validator, answer',
                             INPUTS_RELEASE_NOTES_EXISTS_VALIDATION)
    def test_is_release_notes_exists(self, source_dummy, target_dummy,
                                     source_release_notes, target_release_notes, validator, answer, mocker):
        # type: (str, str, str, str, Type[ContentEntityValidator], Any, Any) -> None
        try:
            copyfile(source_dummy, target_dummy)
            copyfile(source_release_notes, target_release_notes)
            mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
            mocker.patch.object(OldReleaseNotesValidator, 'get_master_diff', side_effect=self.mock_get_master_diff)
            res_validator = OldReleaseNotesValidator(target_dummy)
            assert res_validator.validate_file_release_notes_exists() is answer
        finally:
            os.remove(target_dummy)
            os.remove(target_release_notes)

    @staticmethod
    def create_release_notes_structure_test_package():
        changelog_needed = [
            (VALID_SCRIPT_PATH, 'Script'),
            (VALID_INTEGRATION_TEST_PATH, 'Integration')
        ]

        changelog_files_answer = [
            (VALID_ONE_LINE_CHANGELOG_PATH, True),
            (VALID_ONE_LINE_LIST_CHANGELOG_PATH, True),
            (VALID_MULTI_LINE_CHANGELOG_PATH, True),
            (VALID_MULTI_LINE_LIST_CHANGELOG_PATH, True),
            (INVALID_ONE_LINE_1_CHANGELOG_PATH, False),
            (INVALID_ONE_LINE_2_CHANGELOG_PATH, False),
            (INVALID_ONE_LINE_LIST_1_CHANGELOG_PATH, False),
            (INVALID_ONE_LINE_LIST_2_CHANGELOG_PATH, False),
            (INVALID_MULTI_LINE_1_CHANGELOG_PATH, False),
            (INVALID_MULTI_LINE_2_CHANGELOG_PATH, False)
        ]

        test_package = list()

        for (dummy_file, file_type) in changelog_needed:
            for (release_notes_file, answer) in changelog_files_answer:
                if file_type == 'Script':
                    test_package.append((dummy_file, SCRIPT_TARGET, release_notes_file,
                                         SCRIPT_RELEASE_NOTES_TARGET, OldReleaseNotesValidator, answer))
                elif file_type == 'Integration':
                    test_package.append((dummy_file, INTEGRATION_TARGET, release_notes_file,
                                         INTEGRATION_RELEASE_NOTES_TARGET, OldReleaseNotesValidator, answer))

        return test_package

    test_package = create_release_notes_structure_test_package.__func__()

    @pytest.mark.parametrize('source_dummy, target_dummy, source_release_notes, target_release_notes, '
                             'validator, answer', test_package)
    def test_valid_release_notes_structure(self, source_dummy, target_dummy,
                                           source_release_notes, target_release_notes, validator, answer, mocker):
        # type: (str, str, str, str, Type[ContentEntityValidator], Any, Any) -> None
        try:
            copyfile(source_dummy, target_dummy)
            copyfile(source_release_notes, target_release_notes)
            mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
            mocker.patch.object(OldReleaseNotesValidator, 'get_master_diff', side_effect=self.mock_get_master_diff)
            res_validator = OldReleaseNotesValidator(target_dummy)
            assert res_validator.is_valid_release_notes_structure() is answer
        finally:
            os.remove(target_dummy)
            os.remove(target_release_notes)

    @staticmethod
    def mock_get_master_diff():
        return 'Comment.'

    INPUTS_IS_ID_EQUALS_NAME = [
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, True, ScriptValidator),
        (INVALID_SCRIPT_PATH, SCRIPT_TARGET, False, ScriptValidator),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, True, PlaybookValidator),
        (INVALID_PLAYBOOK_ID_PATH, PLAYBOOK_TARGET, False, PlaybookValidator),
        (VALID_INTEGRATION_ID_PATH, INTEGRATION_TARGET, True, IntegrationValidator),
        (INVALID_INTEGRATION_ID_PATH, INTEGRATION_TARGET, False, IntegrationValidator)
    ]

    @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_ID_EQUALS_NAME)
    def test_is_id_equals_name(self, source, target, answer, validator):
        # type: (str, str, Any, Type[Union[ScriptValidator, PlaybookValidator, IntegrationValidator]]) -> None
        try:
            copyfile(str(source), target)
            structure = StructureValidator(str(source))
            res_validator = validator(structure)
            assert res_validator.is_id_equals_name() is answer
        finally:
            os.remove(target)

    INPUTS_IS_CONNECTED_TO_ROOT = [
        (INVALID_PLAYBOOK_PATH_FROM_ROOT, False),
        (VALID_TEST_PLAYBOOK_PATH, True)
    ]

    @pytest.mark.parametrize('source, answer', INPUTS_IS_CONNECTED_TO_ROOT)
    def test_is_root_connected_to_all_tasks(self, source, answer):
        # type: (str, bool) -> None
        try:
            copyfile(source, PLAYBOOK_TARGET)
            structure = StructureValidator(source)
            validator = PlaybookValidator(structure)
            assert validator.is_root_connected_to_all_tasks() is answer
        finally:
            os.remove(PLAYBOOK_TARGET)

    INPUTS_STRUCTURE_VALIDATION = [
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET, 'integration'),
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, 'script'),
        (VALID_DASHBOARD_PATH, DASHBOARD_TARGET, 'dashboard'),
        (VALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, 'incidentfield'),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, 'playbook'),
        (VALID_REPUTATION_PATH, INDICATOR_TYPE_TARGET, 'reputation'),
        (VALID_INCIDENT_TYPE_PATH, INCIDENT_TYPE_TARGET, 'incidenttype'),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_RELEASE_NOTES_TARGET, 'integration')
    ]

    @pytest.mark.parametrize('source, target, file_type', INPUTS_STRUCTURE_VALIDATION)
    def test_is_file_structure(self, source, target, file_type):
        # type: (str, str, str) -> None
        try:
            copyfile(source, target)
            assert StructureValidator(file_path=source, predefined_scheme=file_type).is_valid_file()
        finally:
            os.remove(target)

    FILES_PATHS_FOR_ALL_VALIDATIONS = [
        VALID_INTEGRATION_ID_PATH,
        VALID_TEST_PLAYBOOK_PATH,
        VALID_SCRIPT_PATH,
        VALID_DASHBOARD_PATH,
        VALID_INCIDENT_FIELD_PATH,
        VALID_REPUTATION_PATH,
        VALID_INCIDENT_TYPE_PATH,
        VALID_BETA_INTEGRATION,
        VALID_INDICATOR_FIELD_PATH,
        VALID_LAYOUT_PATH,
        VALID_MD
    ]

    @pytest.mark.parametrize('file_path', FILES_PATHS_FOR_ALL_VALIDATIONS)
    def test_run_all_validations_on_file(self, mocker, file_path):
        """
        Given
        - A file in packs or beta integration

        When
        - running run_all_validations_on_file on that file

        Then
        -  The file will be validated
        """
        mocker.patch.object(ImageValidator, 'is_valid', return_value=True)
        mocker.patch.object(PlaybookValidator, 'is_script_id_valid', return_value=True)
        mocker.patch.object(ScriptValidator, 'is_valid_script_file_path', return_value=True)
        mocker.patch.object(ScriptValidator, 'is_there_separators_in_names', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_integration_file_path', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_there_separators_in_names', return_value=True)
        validate_manager = ValidateManager(file_path=file_path, skip_conf_json=True)
        assert validate_manager.run_validation_on_specific_files()

    INVALID_FILES_PATHS_FOR_ALL_VALIDATIONS = [
        INVALID_DASHBOARD_PATH,
        INVALID_INCIDENT_FIELD_PATH,
        INVALID_INTEGRATION_ID_PATH,
        INVALID_INTEGRATION_NO_TESTS,
        INVALID_INTEGRATION_NON_CONFIGURED_TESTS,
        INVALID_LAYOUT_CONTAINER_PATH,
        INVALID_LAYOUT_PATH,
        INVALID_PLAYBOOK_CONDITION_1,
        INVALID_PLAYBOOK_CONDITION_2,
        INVALID_PLAYBOOK_ID_PATH,
        INVALID_PLAYBOOK_PATH,
        INVALID_PLAYBOOK_PATH_FROM_ROOT,
        INVALID_REPUTATION_PATH,
        INVALID_SCRIPT_PATH,
        INVALID_WIDGET_PATH,
        INVALID_BETA_INTEGRATION
    ]

    @pytest.mark.parametrize('file_path', INVALID_FILES_PATHS_FOR_ALL_VALIDATIONS)
    @patch.object(ImageValidator, 'is_valid', return_value=True)
    def test_run_all_validations_on_file_failed(self, _, file_path):
        """
        Given
        - An invalid file inside a pack

        When
        - running run_all_validations_on_file on that file

        Then
        -  The file will be validated and failed
        """
        validate_manager = ValidateManager(file_path=file_path, skip_conf_json=True)
        assert not validate_manager.run_validation_on_specific_files()

    def test_run_all_validations_on_file_with_modified_id(self, mocker, integration):
        """
        Given
        - Integration with a modified ID.

        When
        - running 'run_all_validations_on_file' on that file.

        Then
        -  The file will fail validation because its id changed.
        """
        validator = StructureValidator(file_path=integration.yml.path, predefined_scheme='integration')
        old = validator.load_data_from_file()
        old['commonfields']['id'] = 'old_id'

        mocker.patch.object(ImageValidator, 'is_valid', return_value=True)
        mocker.patch('demisto_sdk.commands.common.hook_validations.structure.is_file_path_in_pack', return_value=True)
        mocker.patch('demisto_sdk.commands.common.hook_validations.structure.get_remote_file', return_value=old)

        validate_manager = ValidateManager(skip_conf_json=True)
        assert not validate_manager.run_validations_on_file(file_path=integration.yml.path,
                                                            pack_error_ignore_list=[], is_modified=True)

    def test_files_validator_validate_pack_unique_files(self):
        validate_manager = ValidateManager(skip_conf_json=True)
        result = validate_manager.validate_pack_unique_files(VALID_PACK, pack_error_ignore_list={})
        assert result

    def test_validate_pack_dependencies(self):
        """
            Given:
                - A file path with valid pack dependencies
            When:
                - checking validity of pack dependencies for added or modified files
            Then:
                - return a True validation response
        """
        id_set_path = os.path.normpath(
            os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files', 'id_set', 'id_set.json'))
        validate_manager = ValidateManager(skip_conf_json=True, id_set_path=id_set_path)
        result = validate_manager.validate_pack_unique_files(VALID_PACK, pack_error_ignore_list={})
        assert result

    def test_validate_pack_dependencies__invalid(self, mocker):
        """
            Given:
                - A file path with invalid pack dependencies
            When:
                - checking validity of pack dependencies for added or modified files
            Then:
                - return a False validation response
        """
        id_set_path = os.path.normpath(
            os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files', 'id_set', 'id_set.json'))
        validate_manager = ValidateManager(skip_conf_json=True, id_set_path=id_set_path)
        mocker.patch.object(PackUniqueFilesValidator, 'validate_pack_readme_and_pack_description', return_value=True)
        result = validate_manager.validate_pack_unique_files('QRadar', pack_error_ignore_list={})
        assert not result

    @staticmethod
    def mock_unifier():
        def get_script_or_integration_package_data_mock(*args, **kwargs):
            return VALID_SCRIPT_PATH, ''

        with patch.object(Unifier, '__init__', lambda a, b: None):
            Unifier.get_script_or_integration_package_data = get_script_or_integration_package_data_mock
            return Unifier('')

    def test_script_valid_rn(self, mocker):
        """
            Given:
                - A valid script path
            When:
                - checking validity of added files
            Then:
                - return a True validation response
        """
        mocker.patch.object(ScriptValidator, 'is_valid_name', return_value=True)
        mocker.patch.object(ScriptValidator, 'is_valid_script_file_path', return_value=True)
        mocker.patch.object(ScriptValidator, 'is_there_separators_in_names', return_value=True)
        self.mock_unifier()
        validate_manager = ValidateManager(skip_conf_json=True)
        is_valid = validate_manager.validate_added_files([VALID_SCRIPT_PATH], None)
        assert is_valid

    def test_pack_validation(self):
        validate_manager = ValidateManager(file_path=VALID_PACK, skip_conf_json=True)
        is_valid = validate_manager.run_validation_on_package(VALID_PACK, None)
        assert is_valid

    VALID_ADDED_RELEASE_NOTES = {
        'Packs/HelloWorld/ReleaseNotes/1_2_0.md',
        'Packs/ThreatIntelligenceManagement/ReleaseNotes/1_1_0.md'
        'Packs/Tanium/ReleaseNotes/1_1_0.md'
    }
    INVALID_ADDED_RELEASE_NOTES = {
        'Packs/HelloWorld/ReleaseNotes/1_2_0.md',
        'Packs/HelloWorld/ReleaseNotes/1_3_0.md',
        'Packs/ThreatIntelligenceManagement/ReleaseNotes/1_1_0.md'
        'Packs/Tanium/ReleaseNotes/1_1_0.md'
    }
    VERIFY_NO_DUP_RN_INPUT = [
        (VALID_ADDED_RELEASE_NOTES, True),
        (INVALID_ADDED_RELEASE_NOTES, False)
    ]

    @pytest.mark.parametrize('added_files, expected', VERIFY_NO_DUP_RN_INPUT)
    def test_verify_no_dup_rn(self, added_files: set, expected: bool):
        """
            Given:
                - A list of added files
            When:
                - verifying there are no other new release notes.
            Then:
                - return a validation response
            Case 1: Release notes in different packs.
            Case 2: Release notes where one is in the same pack
        """
        validate_manager = ValidateManager(skip_conf_json=True)
        result = validate_manager.validate_no_duplicated_release_notes(added_files)
        assert result is expected

    ARE_TEST_CONFIGURED_TEST_INPUT = [
        (VALID_INTEGRATION_TEST_PATH, 'integration', True),
        (INVALID_INTEGRATION_NO_TESTS, 'integration', False),
        (INVALID_INTEGRATION_NON_CONFIGURED_TESTS, 'integration', False),
        (TEST_PLAYBOOK, 'testplaybook', False)
    ]

    @pytest.mark.parametrize('file_path, file_type, expected', ARE_TEST_CONFIGURED_TEST_INPUT)
    def test_are_tests_configured(self, file_path: str, file_type: str, expected: bool):
        """
            Given
            - A content item

            When
            - Checking if the item has tests configured

            Then
            -  validator return the correct answer accordingly
        """
        structure_validator = StructureValidator(file_path, predefined_scheme=file_type)
        validator = IntegrationValidator(structure_validator)
        assert validator.are_tests_configured() == expected

    def test_unified_files_ignored(self):
        """
            Given
            - A unified yml file
            When
            - Validating it
            Then
            -  validator should ignore those files
        """
        validate_manager = ValidateManager()
        assert validate_manager.run_validations_on_file(INVALID_IGNORED_UNIFIED_INTEGRATION, None)

    def test_non_integration_png_files_ignored(self):
        """
            Given
            - A png file
            When
            - Validating it
            Then
            -  validator should ignore those files and return False
        """
        validate_manager = ValidateManager()
        assert validate_manager.run_validations_on_file(IGNORED_PNG, None) is False

    def test_test_playbook_with_no_default_version(self):
        validate_manager = ValidateManager(create_id_set=False, silence_init_prints=True)
        is_valid = validate_manager.run_validations_on_file(INVALID_TEST_PLAYBOOK_NO_DEFAULT_VERSION, None)
        assert not is_valid

    def test_get_error_ignore_list(self, mocker):
        """
            Given:
                - A file path to pack ignore
            When:
                - running get_error_ignore_list from validate manager
            Then:
                - verify that the created ignored_errors list is correct
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path, 'fake_pack/.pack-ignore')

        mocker.patch.object(demisto_sdk.commands.validate.validate_manager,
                            'get_pack_ignore_file_path', return_value=test_file)

        validate_manager = ValidateManager()
        ignore_errors_list = validate_manager.get_error_ignore_list("fake")
        assert ignore_errors_list['file_name'] == ['BA101', 'SC101', 'BA106']
        assert 'SC100' not in ignore_errors_list['file_name']

    def test_create_ignored_errors_list(self):
        validate_manager = ValidateManager()
        errors_to_check = ["IN", "SC", "CJ", "DA", "DB", "DO", "ID", "DS", "IM", "IF", "IT", "RN", "RM", "PA", "PB",
                           "WD", "RP", "BA100", "BC100", "ST", "CL", "MP", "LO"]
        ignored_list = validate_manager.create_ignored_errors_list(errors_to_check)
        assert ignored_list == ["BA101", "BA102", "BA103", "BA104", "BA105", "BA106", "BA107", "BA108", "BA109",
                                "BC101", "BC102", "BC103", "BC104"]

    def test_added_files_type_using_function(self, repo, mocker):
        """
            Given:
                - A list of errors that should be checked
            When:
                - Running create_ignored_errors_list from validate manager
            Then:
                - verify that the ignored error list that comes out is correct
        """

        mocker.patch.object(BaseValidator, 'check_file_flags', return_value='')
        saved_stdout = sys.stdout
        pack = repo.create_pack('pack')
        pack.create_test_script()
        with ChangeCWD(pack.repo_path):
            os.system('mv Packs/pack/Scripts/sample_script/sample_script.yml Packs/pack/TestPlaybooks/')
            x = ValidateManager()
            try:
                out = StringIO()
                sys.stdout = out

                x.validate_added_files({'Packs/pack/TestPlaybooks/sample_script.yml'}, None)
                assert 'Missing id in root' not in out.getvalue()
            except Exception:
                assert False
            finally:
                sys.stdout = saved_stdout

    def test_is_old_file_format_non_unified(self):
        """
            Given:
                - A file path which contains a non unified python script
            When:
                - running is_old_file_format on the file
            Then:
                - return a False
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path, 'CortexXDR',
                                 'Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml')
        validate_manager = ValidateManager()
        res = validate_manager.is_old_file_format(test_file, FileType.INTEGRATION)
        assert res is False

    def test_is_old_file_format_unified(self):
        """
            Given:
                - A file path which contains a python script in a legacy yml schema
            When:
                - running is_old_file_format on the file
            Then:
                - return a True
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path,
                                 'UnifiedIntegrations/Integrations/integration-Symantec_Messaging_Gateway.yml')
        validate_manager = ValidateManager()
        res = validate_manager.is_old_file_format(test_file, FileType.INTEGRATION)
        assert res is True

    def test_validate_no_missing_release_notes__no_missing_rn(self, repo):
        """
            Given:
                - packs with modified files, modified old format files and release notes for all of them
            When:
                - running validate_no_missing_release_notes on the files
            Then:
                - return a True as no release notes are missing
        """
        pack1 = repo.create_pack('PackName1')
        incident_field1 = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        pack2 = repo.create_pack('PackName2')
        incident_field2 = pack2.create_incident_field('incident-field', content=INCIDENT_FIELD)
        validate_manager = ValidateManager()
        pack3 = repo.create_pack('PackName3')
        incident_field3 = pack3.create_incident_field('incident-field', content=INCIDENT_FIELD)

        modified_files = {incident_field1.get_path_from_pack(),
                          incident_field2.get_path_from_pack()}
        old_format_files = {incident_field3.get_path_from_pack()}
        added_files = {'Packs/PackName1/ReleaseNotes/1_0_0.md',
                       'Packs/PackName2/ReleaseNotes/1_1_1.md',
                       'Packs/PackName3/ReleaseNotes/1_1_1.md'}

        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files=modified_files,
                                                                      old_format_files=old_format_files,
                                                                      added_files=added_files) is True

    def test_validate_no_missing_release_notes__missing_rn_in_modified_files(self, repo, mocker):
        """
            Given:
                - 2 packs with modified files and release notes for only one and no old format files
            When:
                - running validate_no_missing_release_notes on the files
            Then:
                - return a False as there are release notes missing
        """
        mocker.patch.object(BaseValidator, "update_checked_flags_by_support_level", return_value="")
        pack1 = repo.create_pack('PackName1')
        incident_field1 = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        pack2 = repo.create_pack('PackName2')
        incident_field2 = pack2.create_incident_field('incident-field', content=INCIDENT_FIELD)
        validate_manager = ValidateManager()
        modified_files = {incident_field1.get_path_from_pack(),
                          incident_field2.get_path_from_pack()}
        added_files = {'Packs/PackName1/ReleaseNotes/1_0_0.md'}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files=modified_files,
                                                                      old_format_files=set(),
                                                                      added_files=added_files) is False

    def test_validate_no_missing_release_notes__missing_rn_dependent_on_api_module(self, repo, mocker, tmpdir):
        """
            Given:
                - APIModule pack has a change relevant for another pack
                - APIModule modified files and release notes present
                - dependent pack has NO CHANGES
                - dependent pack release notes are missing
            When:
                - running validate_no_missing_release_notes on the file
            Then:
                - return a False as there are release notes missing
        """
        mocker.patch.object(BaseValidator, "update_checked_flags_by_support_level", return_value="")
        pack1 = repo.create_pack('ApiModules')
        api_script1 = pack1.create_script('APIScript')
        pack2_name = 'ApiDependent'
        pack2 = repo.create_pack(pack2_name)
        integration2 = pack2.create_integration(pack2_name)
        id_set_content = {'integrations':
                          [
                              {'ApiDependent':
                               {
                                   'name': integration2.name,
                                   'file_path': integration2.path,
                                   'pack': pack2_name,
                                   'api_modules': api_script1.name
                               }
                               }
                          ]
                          }
        id_set_f = tmpdir / "id_set.json"
        id_set_f.write(json.dumps(id_set_content))
        validate_manager = ValidateManager(id_set_path=id_set_f.strpath)
        modified_files = {api_script1.yml.rel_path}
        added_files = {'Packs/ApiModules/ReleaseNotes/1_0_0.md'}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files=modified_files,
                                                                      old_format_files=set(),
                                                                      added_files=added_files) is False

    def test_validate_no_missing_release_notes__happy_rn_dependent_on_api_module(self, repo, mocker, tmpdir):
        """
            Given:
                - APIModule pack has a change relevant for another pack
                - APIModule modified files and release notes present
                - dependent pack has NO CHANGES
                - dependent pack has release notes
            When:
                - running validate_no_missing_release_notes on the file
            Then:
                - return a True as there are no release notes missing
        """
        mocker.patch.object(BaseValidator, "update_checked_flags_by_support_level", return_value="")
        pack1 = repo.create_pack('ApiModules')
        api_script1 = pack1.create_script('APIScript')
        pack2_name = 'ApiDependent'
        pack2 = repo.create_pack(pack2_name)
        integration2 = pack2.create_integration(pack2_name)
        id_set_content = {'integrations':
                          [
                              {'ApiDependent':
                               {'name': integration2.name,
                                'file_path': integration2.path,
                                'pack': pack2_name,
                                'api_modules': api_script1.name
                                }
                               }
                          ]}
        id_set_f = tmpdir / "id_set.json"
        id_set_f.write(json.dumps(id_set_content))
        validate_manager = ValidateManager(id_set_path=id_set_f.strpath)
        modified_files = {api_script1.yml.rel_path}
        added_files = {'Packs/ApiModules/ReleaseNotes/1_0_0.md', 'Packs/ApiDependent/ReleaseNotes/1_0_0.md'}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files=modified_files,
                                                                      old_format_files=set(),
                                                                      added_files=added_files) is True

    def test_validate_no_missing_release_notes__missing_rn_in_old_format_files(self, repo, mocker):
        """
            Given:
                - 2 packs one modified files the other an old format file and release notes for only one
            When:
                - running validate_no_missing_release_notes on the files
            Then:
                - return a False as there are release notes missing
        """
        mocker.patch.object(BaseValidator, "update_checked_flags_by_support_level", return_value="")
        pack1 = repo.create_pack('PackName1')
        incident_field1 = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        pack2 = repo.create_pack('PackName2')
        incident_field2 = pack2.create_incident_field('incident-field', content=INCIDENT_FIELD)
        validate_manager = ValidateManager()
        modified_files = {incident_field1.get_path_from_pack()}
        added_files = {'Packs/PackName1/ReleaseNotes/1_0_0.md'}
        old_format_files = {incident_field2.get_path_from_pack()}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files=modified_files,
                                                                      old_format_files=old_format_files,
                                                                      added_files=added_files) is False

    def test_validate_no_missing_release_notes__missing_rn_for_added_file_in_existing_pack(self, repo, mocker):
        """
            Given:
                - an existing pack with an added file which does not have release notes
            When:
                - running validate_no_missing_release_notes on the files
            Then:
                - return a False as there are release notes missing
        """
        mocker.patch.object(BaseValidator, "update_checked_flags_by_support_level", return_value="")
        pack1 = repo.create_pack('PackName1')
        incident_field1 = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        validate_manager = ValidateManager()
        added_files = {incident_field1.get_path_from_pack()}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files=set(), old_format_files=set(),
                                                                      added_files=added_files) is False

    def test_validate_no_missing_release_notes__no_missing_rn_new_pack(self, repo, mocker):
        """
            Given:
                - an added file in a new pack
            When:
                - running validate_no_missing_release_notes on the files
            Then:
                - return a True as there are no release notes missing
        """
        mocker.patch.object(BaseValidator, "update_checked_flags_by_support_level", return_value="")
        pack1 = repo.create_pack('PackName1')
        incident_field1 = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        validate_manager = ValidateManager()
        validate_manager.new_packs = {'PackName1'}
        added_files = {incident_field1.get_path_from_pack()}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files=set(),
                                                                      old_format_files=set(),
                                                                      added_files=added_files) is True

    def test_validate_no_old_format__with_toversion(self):
        """
            Given:
                - an old format_file with toversion
            When:
                - running validate_no_old_format on the file
            Then:
                - return a True as the file is valid
        """
        validate_manager = ValidateManager()
        old_format_files = {"demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/"
                            "script-SampleScriptPackageSanityDocker45_45.yml"}
        assert validate_manager.validate_no_old_format(old_format_files)

    def test_validate_no_old_format__without_toversion(self, mocker):
        """
            Given:
                - 2 old format_file without toversion
            When:
                - running validate_no_old_format on the files
            Then:
                - return a False as the files are invalid
                - assert the handle_error function is called for each file (and 1 for not finding the id set file)
        """
        handle_error_mock = mocker.patch.object(BaseValidator, "handle_error", return_value="not-a-non-string")
        validate_manager = ValidateManager()
        old_format_files = {"demisto_sdk/tests/test_files/script-valid.yml",
                            "demisto_sdk/tests/test_files/integration-test.yml"}
        assert not validate_manager.validate_no_old_format(old_format_files)
        assert handle_error_mock.call_count == 3

    def test_validate_no_old_format_deprecated_content(self, repo):
        """
            Given:
                - a pack with a script in old format_file with deprecated: true
                - a script in old format_file with deprecated: false
                - a script in old format_file without deprecated field
            When:
                - running validate_no_old_format on the file
            Then:
                - return True for the first script as the file is valid
                - return False for script2 and scrupt3 - validate should fail and raise [ST106] error.
        """
        validate_manager = ValidateManager()
        pack1 = repo.create_pack('Pack1')
        script = pack1.create_script('Script1')
        script2 = pack1.create_script('Script2')
        script3 = pack1.create_script('Script3')
        script.yml.write_dict({"script": "\n\n\ndef main():\n    return_error('Not implemented.')\n\u200B\n"
                                         "if __name__\\ in ('builtins', '__builtin__', '__main__'):\n    main()\n",
                               "deprecated": True})
        script2.yml.write_dict({"script": "\n\n\ndef main():\n    return_error('Not implemented.')\n\u200B\n"
                                          "if __name__\\ in ('builtins', '__builtin__', '__main__'):\n    main()\n",
                                "deprecated": False})
        script3.yml.write_dict({"script": "\n\n\ndef main():\n    return_error('Not implemented.')\n\u200B\n"
                                          "if __name__\\ in ('builtins', '__builtin__', '__main__'):\n    main()\n"})
        old_format_file = {script.yml.path}
        deprecated_false_file = {script2.yml.path, script3.yml.path}
        assert validate_manager.validate_no_old_format(old_format_file)
        assert not validate_manager.validate_no_old_format(deprecated_false_file)

    def test_setup_git_params_master_branch(self, mocker):
        mocker.patch.object(GitUtil, 'get_current_working_branch', return_value='master')
        validate_manager = ValidateManager()
        validate_manager.setup_git_params()

        assert not validate_manager.always_valid
        assert validate_manager.skip_pack_rn_validation

    def test_setup_git_params_non_master_branch(self, mocker):
        mocker.patch.object(GitUtil, 'get_current_working_branch', return_value='not-master-branch')
        validate_manager = ValidateManager()
        validate_manager.setup_git_params()

        assert not validate_manager.always_valid
        assert not validate_manager.skip_pack_rn_validation

    def test_get_packs(self):
        modified_files = {'Packs/CortexXDR/Integrations/XDR_iocs/XDR_iocs.py',
                          'Packs/Claroty/Integrations/Claroty/Claroty.py',
                          'Packs/McAfee_ESM/Integrations/McAfee_ESM_v2/McAfee_ESM_v2.yml',
                          'Packs/Malware/IncidentTypes/incidenttype-Malware.json',
                          'Packs/Claroty/Layouts/layoutscontainer-Claroty_Integrity_Incident.json'}
        packs = {'CortexXDR', 'Claroty', 'McAfee_ESM', 'Malware'}
        validate_manager = ValidateManager(skip_conf_json=True)
        packs_found = validate_manager.get_packs(modified_files)
        assert packs_found == packs

    def test_validate_release_notes(self, mocker):
        """
        Given
            - A valid release note file.
        When
            - Run the validate command.
        Then
            - validate_release_notes returns True
        """
        file_path = 'Packs/CortexXDR/ReleaseNotes/1_1_1.md'
        modified_files = {'Packs/CortexXDR/Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml'}
        mocker.patch.object(ReleaseNotesValidator, '__init__', return_value=None)
        mocker.patch.object(ReleaseNotesValidator, 'is_file_valid', return_value=True)
        validate_manager = ValidateManager(skip_conf_json=True)
        assert validate_manager.validate_release_notes(file_path, {}, modified_files, None, False)

    def test_validate_release_notes__invalid_rn_for_new_pack(self, mocker):
        """
        Given
            - A release note file for a newly created pack.
        When
            - Run the validate command.
        Then
            - validate_release_notes returns False
        """

        file_path = 'Packs/CortexXDR/ReleaseNotes/1_0_0.md'
        modified_files = {'Packs/CortexXDR/Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml'}
        mocker.patch.object(ReleaseNotesValidator, '__init__', return_value=None)
        mocker.patch.object(ReleaseNotesValidator, 'is_file_valid', return_value=True)
        mocker.patch.object(BaseValidator, 'handle_error', return_value="ReleaseNotes for newly created pack")
        validate_manager = ValidateManager(skip_conf_json=True)
        validate_manager.new_packs = {'CortexXDR'}
        assert validate_manager.validate_release_notes(file_path, {file_path}, modified_files, None, False) is False


@pytest.mark.parametrize('pack_name, expected', [
    ('NonSupported', False),
    ('PackName1', True)
])
def test_should_raise_pack_version(pack_name, expected):
    """
    Given
        - NonSupported Pack - Should return False as no need to bump the pack version.
        - Regular pack - should result as True, the pack version should be raised
    When
        - Run should_raise_pack_version command.
    Then
        - validate should_raise_pack_version runs as expected.
    """
    validate_manager = ValidateManager()
    res = validate_manager.should_raise_pack_version(pack_name)
    assert res == expected


def test_run_validation_using_git_on_only_metadata_changed(mocker):
    """
    Given
        - metadata file that was changed.
    When
        - Run all tests on the file.
    Then
        - validate That no error returns.
    """
    mocker.patch.object(ValidateManager, 'setup_git_params')
    mocker.patch.object(ValidateManager, 'get_changed_files_from_git',
                        return_value=(set(), set(), {'/Packs/TestPack/pack_metadata.json'}, set()))

    validate_manager = ValidateManager()
    res = validate_manager.run_validation_using_git()
    assert res


def test_is_mapping_fields_command_exist(integration):
    """
        Given
        - Integration yml file with get-mapping-fields command.

        When
        - Checking if get-mapping-fields command exists.

        Then
        -  validator returns the True.
    """
    integration.yml.write_dict({'script': {
        'commands': [{
            'name': 'get-mapping-fields'
        }],
        'ismappable': True
    }})
    structure_validator = StructureValidator(integration.yml.path, predefined_scheme='integration')
    validator = IntegrationValidator(structure_validator)

    assert validator.is_mapping_fields_command_exist()


def test_mapping_fields_command_dont_exist(integration):
    """
        Given
        - Integration yml file with no get-mapping-fields command and ismappable: True.

        When
        - Checking if get-mapping-fields command exists.

        Then
        -  validator returns the False. The field ismappable exists, but the command no.
    """
    integration.yml.write_dict({'script': {
        'commands': [{
            'name': 'not-get-mapping-fields'
        }],
        'ismappable': True
    }})
    structure_validator = StructureValidator(integration.yml.path, predefined_scheme='integration')
    validator = IntegrationValidator(structure_validator)

    assert not validator.is_mapping_fields_command_exist()


def test_get_packs_that_should_have_version_raised(repo):
    """
       Given
       - Different files from different packs in several statuses:
         1. Modified integration
         2. Modified test-playbook
         3. Added script to new pack
         4. Added script to existing pack
         5. Modified old format script

       When
       - Running get_packs_that_should_have_version_raised.

       Then
       -  The returning set includes the packs for 1, 4 & 5 and does not include the packs for 2 & 3.
   """
    existing_pack1 = repo.create_pack('PackWithModifiedIntegration')
    moodified_integration = existing_pack1.create_integration('MyIn')
    moodified_integration.create_default_integration()

    existing_pack2 = repo.create_pack('ExistingPackWithAddedScript')
    added_script_existing_pack = existing_pack2.create_script('MyScript')
    added_script_existing_pack.create_default_script()

    new_pack = repo.create_pack('NewPack')
    added_script_new_pack = new_pack.create_script('MyNewScript')
    added_script_new_pack.create_default_script()

    existing_pack3 = repo.create_pack('PackWithModifiedOldFile')
    modified_old_format_script = existing_pack3.create_script('OldScript')
    modified_old_format_script.create_default_script()

    existing_pack4 = repo.create_pack('PackWithModifiedTestPlaybook')
    moodified_test_playbook = existing_pack4.create_test_playbook('TestBook')
    moodified_test_playbook.create_default_test_playbook()

    validate_manager = ValidateManager()
    validate_manager.new_packs = {'NewPack'}

    modified_files = {moodified_integration.yml.rel_path, moodified_test_playbook.yml.rel_path}
    added_files = {added_script_existing_pack.yml.rel_path, added_script_new_pack.yml.rel_path}
    old_files = {modified_old_format_script.yml.rel_path}

    with ChangeCWD(repo.path):
        packs_that_should_have_version_raised = validate_manager.get_packs_that_should_have_version_raised(
            modified_files=modified_files, added_files=added_files, old_format_files=old_files)

        assert 'PackWithModifiedIntegration' in packs_that_should_have_version_raised
        assert 'ExistingPackWithAddedScript' in packs_that_should_have_version_raised
        assert 'PackWithModifiedOldFile' in packs_that_should_have_version_raised
        assert 'PackWithModifiedTestPlaybook' not in packs_that_should_have_version_raised
        assert 'NewPack' not in packs_that_should_have_version_raised


def test_quite_bc_flag(repo):
    existing_pack1 = repo.create_pack('PackWithModifiedIntegration')
    moodified_integration = existing_pack1.create_integration('MyIn')
    moodified_integration.create_default_integration()
