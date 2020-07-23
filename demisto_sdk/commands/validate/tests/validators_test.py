import json
import os
import sys
from io import StringIO
from shutil import copyfile
from typing import Any, Type, Union

import pytest
from demisto_sdk.commands.common.constants import CONF_PATH, TEST_PLAYBOOK
from demisto_sdk.commands.common.git_tools import git_path
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
from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.hook_validations.reputation import \
    ReputationValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.validate.file_validator import FilesValidator
from demisto_sdk.commands.validate.validate_manager import ValidateManager
from demisto_sdk.tests.constants_test import (
    CONF_JSON_MOCK_PATH, DASHBOARD_TARGET, DIR_LIST,
    GIT_HAVE_MODIFIED_AND_NEW_FILES, INCIDENT_FIELD_TARGET,
    INCIDENT_TYPE_TARGET, INDICATOR_TYPE_TARGET,
    INTEGRATION_RELEASE_NOTES_TARGET, INTEGRATION_TARGET,
    INVALID_DASHBOARD_PATH, INVALID_IGNORED_UNIFIED_INTEGRATION,
    INVALID_INCIDENT_FIELD_PATH, INVALID_INTEGRATION_ID_PATH,
    INVALID_INTEGRATION_NO_TESTS, INVALID_INTEGRATION_NON_CONFIGURED_TESTS,
    INVALID_LAYOUT_CONTAINER_PATH, INVALID_LAYOUT_PATH,
    INVALID_MULTI_LINE_1_CHANGELOG_PATH, INVALID_MULTI_LINE_2_CHANGELOG_PATH,
    INVALID_NO_HIDDEN_PARAMS, INVALID_ONE_LINE_1_CHANGELOG_PATH,
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
    VALID_NO_HIDDEN_PARAMS, VALID_ONE_LINE_CHANGELOG_PATH,
    VALID_ONE_LINE_LIST_CHANGELOG_PATH, VALID_PACK, VALID_PLAYBOOK_CONDITION,
    VALID_REPUTATION_PATH, VALID_SCRIPT_PATH, VALID_TEST_PLAYBOOK_PATH,
    VALID_WIDGET_PATH, WIDGET_TARGET)
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import \
    INCIDENT_FIELD
from mock import patch
from TestSuite.test_tools import ChangeCWD


class TestValidators:
    CREATED_DIRS = list()  # type: list[str]

    @classmethod
    def setup_class(cls):
        print("Setups class")
        for dir_to_create in DIR_LIST:
            if not os.path.exists(dir_to_create):
                cls.CREATED_DIRS.append(dir_to_create)
                os.makedirs(dir_to_create)
        copyfile(CONF_JSON_MOCK_PATH, CONF_PATH)

    @classmethod
    def teardown_class(cls):
        print("Tearing down class")
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

    @patch.object(OldReleaseNotesValidator, 'get_master_diff', return_value='Comment.')
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
            copyfile(VALID_BETA_PLAYBOOK_PATH, PLAYBOOK_TARGET)
            structure = StructureValidator(VALID_BETA_PLAYBOOK_PATH, predefined_scheme='playbook')
            validator = PlaybookValidator(structure)
            assert validator.is_valid_playbook(validate_rn=False)
        finally:
            os.remove(PLAYBOOK_TARGET)

    @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_VALID_VERSION)
    def test_is_valid_version(self, source, target, answer, validator):
        # type: (str, str, Any, Type[ContentEntityValidator]) -> None
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            res_validator = validator(structure)
            assert res_validator.is_valid_version() is answer
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
    def test_is_file_valid(self, source, target, answer, validator):
        # type: (str, str, Any, Type[ContentEntityValidator]) -> None
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            res_validator = validator(structure)
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

    IS_VALID_HIDDEN_PARAMS = [
        (VALID_NO_HIDDEN_PARAMS, True),
        (INVALID_NO_HIDDEN_PARAMS, False),
    ]

    @pytest.mark.parametrize("source, answer", IS_VALID_HIDDEN_PARAMS)
    def test_is_valid_hidden_params(self, source, answer):
        # type: (str, str) -> None
        structure = StructureValidator(source)
        validator = IntegrationValidator(structure)
        assert validator.is_valid_hidden_params() is answer

    with open(GIT_HAVE_MODIFIED_AND_NEW_FILES, "r") as test_params_file:
        tests_params = json.load(test_params_file)
    params = [
        (None, tuple(set(i) for i in tests_params['data']['params_with_data']), '123456', True, True),
        ('origin/master', tuple(set(i) for i in tests_params['data']['params_with_data']), '123456', True, True),
        (None, tuple(set(i) for i in tests_params['data']['params_with_data']), '', True, True),
        (None, tuple(set(i) for i in tests_params['data']['params_without_data']), '123456', True, True),
        (None, tuple(set(i) for i in tests_params['data']['params_with_data']), '123456', False, False),
    ]

    @pytest.mark.parametrize("prev_var, get_modified_and_added_files, release_iden, answer, is_valid", params)
    def test_validate_against_previous_version(self, prev_var, get_modified_and_added_files, release_iden, answer,
                                               is_valid, mocker):
        file_validator = FilesValidator(skip_conf_json=True, prev_ver=prev_var)
        file_validator._is_valid = is_valid
        mocker.patch.object(FilesValidator, 'get_modified_and_added_files', return_value=get_modified_and_added_files)
        mocker.patch.object(FilesValidator, 'get_content_release_identifier', return_value=release_iden)
        mocker.patch.object(FilesValidator, 'validate_modified_files', return_value=None)

        assert file_validator.validate_against_previous_version() is None
        assert file_validator._is_valid is answer

    INPUTS_STRUCTURE_VALIDATION = [
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET),
        (VALID_SCRIPT_PATH, SCRIPT_TARGET),
        (VALID_DASHBOARD_PATH, DASHBOARD_TARGET),
        (VALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET),
        (VALID_REPUTATION_PATH, INDICATOR_TYPE_TARGET),
        (VALID_INCIDENT_TYPE_PATH, INCIDENT_TYPE_TARGET),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_RELEASE_NOTES_TARGET)
    ]

    @pytest.mark.parametrize('source, target', INPUTS_STRUCTURE_VALIDATION)
    def test_is_file_structure(self, source, target):
        # type: (str, str) -> None
        try:
            copyfile(source, target)
            assert FilesValidator(skip_conf_json=True).is_valid_structure()
        finally:
            os.remove(target)

    FILE_PATHS = [
        ([VALID_INTEGRATION_TEST_PATH], 'integration'),
        ([VALID_TEST_PLAYBOOK_PATH], 'playbook'),
        ([VALID_DASHBOARD_PATH], 'dashboard'),
        ([VALID_INCIDENT_FIELD_PATH], 'incidentfield'),
        ([VALID_REPUTATION_PATH], 'reputation'),
        ([VALID_INCIDENT_TYPE_PATH], 'incidenttype'),
        ([VALID_INTEGRATION_TEST_PATH], 'betaintegration')
    ]

    @pytest.mark.parametrize('file_path, file_type', FILE_PATHS)
    def test_is_valid_rn(self, mocker, file_path, file_type):
        mocker.patch.object(OldReleaseNotesValidator, 'get_master_diff', return_value=None)
        mocker.patch.object(StructureValidator, 'is_valid_file', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_subtype', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_feed', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_description', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_version', return_value=True)
        mocker.patch.object(ImageValidator, 'is_valid', return_value=True)
        mocker.patch.object(DashboardValidator, 'is_id_equals_name', return_value=True)
        mocker.patch.object(ReputationValidator, 'is_id_equals_details', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_beta', return_value=True)
        mocker.patch.object(IntegrationValidator, 'are_tests_configured', return_value=True)
        mocker.patch.object(PlaybookValidator, 'are_tests_configured', return_value=True)
        file_validator = FilesValidator(skip_conf_json=True)
        file_validator.validate_added_files(set(file_path), file_type)
        assert file_validator._is_valid

    FILES_PATHS_FOR_ALL_VALIDATIONS = [
        (VALID_INTEGRATION_ID_PATH, 'integration'),
        (VALID_TEST_PLAYBOOK_PATH, 'playbook'),
        (VALID_SCRIPT_PATH, 'script'),
        (VALID_DASHBOARD_PATH, 'dashboard'),
        (VALID_INCIDENT_FIELD_PATH, 'incidentfield'),
        (VALID_REPUTATION_PATH, 'reputation'),
        (VALID_INCIDENT_TYPE_PATH, 'incidenttype'),
        (VALID_BETA_INTEGRATION, 'betaintegration'),
        (VALID_INDICATOR_FIELD_PATH, 'indicatorfield'),
        (VALID_LAYOUT_PATH, 'layout'),
        (VALID_MD, '')
    ]

    @pytest.mark.parametrize('file_path, file_type', FILES_PATHS_FOR_ALL_VALIDATIONS)
    @patch.object(ImageValidator, 'is_valid', return_value=True)
    def test_run_all_validations_on_file(self, _, file_path, file_type):
        """
        Given
        - A file in packs or beta integration

        When
        - running run_all_validations_on_file on that file

        Then
        -  The file will be validated
        """
        file_validator = FilesValidator(skip_conf_json=True)
        file_validator.run_all_validations_on_file(file_path, file_type)
        assert file_validator._is_valid

    def test_files_validator_validate_pack_unique_files__file_validator(self,):
        files_validator = FilesValidator(skip_conf_json=True)
        files_validator.validate_pack_unique_files({VALID_PACK})
        assert files_validator._is_valid

    def test_files_validator_validate_pack_unique_files__validate_manager(self, ):
        validate_manager = ValidateManager(skip_conf_json=True)
        result = validate_manager.validate_pack_unique_files(VALID_PACK, pack_error_ignore_list={})
        assert result

    def test_validate_pack_dependencies__validate_manager(self, ):
        """
            Given:
                - A file path with valid pack dependencies
            When:
                - checking validity of pack dependencies for added or modified files
            Then:
                - return a True validation response
        """
        validate_manager = ValidateManager(skip_conf_json=True)
        id_set_path = os.path.normpath(
            os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files', 'id_set', 'id_set.json'))
        result = validate_manager.validate_pack_unique_files(VALID_PACK, pack_error_ignore_list={},
                                                             id_set_path=id_set_path)
        assert result

    def test_validate_invalid_pack_dependencies__validate_manager(self, ):
        """
            Given:
                - A file path with invalid pack dependencies
            When:
                - checking validity of pack dependencies for added or modified files
            Then:
                - return a False validation response
        """
        validate_manager = ValidateManager(skip_conf_json=True)
        id_set_path = os.path.normpath(
            os.path.join(__file__, git_path(), 'demisto_sdk', 'tests', 'test_files', 'id_set', 'id_set.json'))
        result = validate_manager.validate_pack_unique_files('QRadar', pack_error_ignore_list={},
                                                             id_set_path=id_set_path)
        assert not result

    FILE_PATH = [
        ([VALID_SCRIPT_PATH], 'script')
    ]

    @staticmethod
    def mock_unifier():
        def get_script_or_integration_package_data_mock(*args, **kwargs):
            return VALID_SCRIPT_PATH, ''
        with patch.object(Unifier, '__init__', lambda a, b: None):
            Unifier.get_script_or_integration_package_data = get_script_or_integration_package_data_mock
            return Unifier('')

    @pytest.mark.parametrize('file_path, file_type', FILE_PATH)
    def test_script_valid_rn(self, mocker, file_path, file_type):
        """
            Given:
                - A valid script path
            When:
                - checking validity of added files
            Then:
                - return a True validation response
        """
        mocker.patch.object(ScriptValidator, 'is_valid_name', return_value=True)
        self.mock_unifier()
        file_validator = FilesValidator(skip_conf_json=True)
        file_validator.validate_added_files(file_path, file_type)
        assert file_validator._is_valid

    def test_pack_validation(self):
        file_validator = FilesValidator(skip_conf_json=True)
        file_validator.file_path = VALID_PACK
        file_validator.is_valid_structure()
        assert file_validator._is_valid is False

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
    def test_verify_no_dup_rn__validate_manager(self, added_files: set, expected: bool):
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

    @pytest.mark.parametrize('added_files, expected', VERIFY_NO_DUP_RN_INPUT)
    def test_verify_no_dup_rn__file_validator(self, added_files: set, expected: bool):
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
        file_validator = FilesValidator(skip_conf_json=True)
        file_validator.verify_no_dup_rn(added_files)
        assert file_validator._is_valid is expected

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
        file_validator = FilesValidator()
        file_validator.validate_modified_files({INVALID_IGNORED_UNIFIED_INTEGRATION})
        assert file_validator._is_valid
        file_validator.validate_added_files({INVALID_IGNORED_UNIFIED_INTEGRATION})
        assert file_validator._is_valid

    def test_get_error_ignore_list__file_validator(self, mocker):
        """
            Given:
                - A file path to pack ignore
            When:
                - running get_error_ignore_list from file validator
            Then:
                - verify that the created ignored_errors list is correct
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path, 'fake_pack/.pack-ignore')

        mocker.patch.object(FilesValidator, 'get_pack_ignore_file_path', return_value=test_file)

        file_validator = FilesValidator()
        ignore_errors_list = file_validator.get_error_ignore_list("fake")
        assert ignore_errors_list['file_name'] == ['BA101', 'IF107']
        assert 'SC100' not in ignore_errors_list['file_name']

    def test_create_ignored_errors_list__file_validator(self):
        """
            Given:
                - A list of errors that should be checked
            When:
                - Running create_ignored_errors_list from file validator
            Then:
                - verify that the ignored error list that comes out is correct
        """
        file_validator = FilesValidator()
        errors_to_check = ["IN", "SC", "CJ", "DA", "DB", "DO", "ID", "DS", "IM", "IF", "IT", "RN", "RM", "PA", "PB",
                           "WD", "RP", "BA100", "BC100", "ST", "CL", "MP", "LO"]
        ignored_list = file_validator.create_ignored_errors_list(errors_to_check)
        assert ignored_list == ["BA101", "BA102", "BA103", "BA104", "BC101", "BC102", "BC103", "BC104"]

    def test_get_error_ignore_list__validate_manager(self, mocker):
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

        mocker.patch.object(ValidateManager, 'get_pack_ignore_file_path', return_value=test_file)

        validate_manager = ValidateManager()
        ignore_errors_list = validate_manager.get_error_ignore_list("fake")
        assert ignore_errors_list['file_name'] == ['BA101', 'IF107']
        assert 'SC100' not in ignore_errors_list['file_name']

    def test_create_ignored_errors_list__validate_manager(self):
        validate_manager = ValidateManager()
        errors_to_check = ["IN", "SC", "CJ", "DA", "DB", "DO", "ID", "DS", "IM", "IF", "IT", "RN", "RM", "PA", "PB",
                           "WD", "RP", "BA100", "BC100", "ST", "CL", "MP", "LO"]
        ignored_list = validate_manager.create_ignored_errors_list(errors_to_check)
        assert ignored_list == ["BA101", "BA102", "BA103", "BA104", "BC101", "BC102", "BC103", "BC104"]

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
            os.mkdir('Packs/pack/TestPlaybooks/')
            os.system('mv Packs/pack/Scripts/sample_script/sample_script.yml Packs/pack/TestPlaybooks/')
            x = FilesValidator()
            try:
                out = StringIO()
                sys.stdout = out

                x.validate_added_files({'Packs/pack/TestPlaybooks/sample_script.yml'})
                assert 'Missing id in root' not in out.getvalue()
            except Exception:
                assert False
            finally:
                sys.stdout = saved_stdout

    def test_is_py_or_yml__validate_manager(self):
        """
            Given:
                - A file path which contains a python script
            When:
                - validating the associated yml file
            Then:
                - return a False validation response
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path, 'CortexXDR',
                                 'Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml')
        validate_manager = ValidateManager()
        res = validate_manager._is_py_script_or_integration(test_file)
        assert res is False

    def test_is_py_or_yml_invalid__validate_manager(self):
        """
            Given:
                - A file path which contains a python script in a legacy yml schema
            When:
                - verifying the yml is valid using validate manager
            Then:
                - return a False validation response
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path,
                                 'UnifiedIntegrations/Integrations/integration-Symantec_Messaging_Gateway.yml')
        validate_manager = ValidateManager()
        res = validate_manager._is_py_script_or_integration(test_file)
        assert res is False

    def test_is_py_or_yml__file_validator(self):
        """
            Given:
                - A file path which contains a python script
            When:
                - verifying the yml is valid using file validator
            Then:
                - return a False validation response
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path, 'CortexXDR',
                                 'Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml')
        file_validator = FilesValidator()
        res = file_validator._is_py_script_or_integration(test_file)
        assert res is False

    def test_is_py_or_yml_invalid__file_validator(self):
        """
            Given:
                - A file path which contains a python script in a legacy yml schema
            When:
                - verifying the yml is valid using file validator
            Then:
                - return a False validation response
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f'{git_path()}/demisto_sdk/tests', 'test_files'))
        test_file = os.path.join(files_path,
                                 'UnifiedIntegrations/Integrations/integration-Symantec_Messaging_Gateway.yml')
        file_validator = FilesValidator()
        res = file_validator._is_py_script_or_integration(test_file)
        assert res is False

    def test_validate_no_missing_release_notes__no_missing_rn(self, repo):
        """
            Given:
                - packs with modified files and release notes
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
        modified_files = {incident_field1.get_path_from_pack(),
                          incident_field2.get_path_from_pack()}
        added_files = {'Packs/PackName1/ReleaseNotes/1_0_0.md',
                       'Packs/PackName2/ReleaseNotes/1_1_1.md'}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files, added_files) is True

    def test_validate_no_missing_release_notes__missing_rn(self, repo):
        """
            Given:
                - 2 packs with modified files and release notes for only one
            When:
                - running validate_no_missing_release_notes on the files
            Then:
                - return a False as there are release notes missing
        """
        pack1 = repo.create_pack('PackName1')
        incident_field1 = pack1.create_incident_field('incident-field', content=INCIDENT_FIELD)
        pack2 = repo.create_pack('PackName2')
        incident_field2 = pack2.create_incident_field('incident-field', content=INCIDENT_FIELD)
        validate_manager = ValidateManager()
        modified_files = {incident_field1.get_path_from_pack(),
                          incident_field2.get_path_from_pack()}
        added_files = {'Packs/PackName1/ReleaseNotes/1_0_0.md'}
        with ChangeCWD(repo.path):
            assert validate_manager.validate_no_missing_release_notes(modified_files, added_files) is False

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
                - an old format_file without toversion
            When:
                - running validate_no_old_format on the file
            Then:
                - return a False as the file is invalid
        """
        mocker.patch.object(BaseValidator, "handle_error", return_value="not-a-non-string")
        validate_manager = ValidateManager()
        old_format_files = {"demisto_sdk/tests/test_files/script-valid.yml"}
        assert not validate_manager.validate_no_old_format(old_format_files)

    def test_filter_changed_files(self, mocker):
        """
            Given:
                - A string of git diff results
            When:
                - running filter_changed_files on the string
            Then:
                - Ensure the modified files are recognized correctly.
                - Ensure the added files are recognized correctly.
                - Ensure the renamed file is in a tup;e in the modified files.
                - Ensure modified metadata files are in the changed_meta_files and that the added one is not.
                - Ensure the added code and meta files are not in added files.
                - Ensure old format file is recognized correctly.
                - Ensure deleted file is recognized correctly.
                - Ensure ignored files are set correctly.
        """
        mocker.patch.object(os.path, 'isfile', return_value=True)
        mocker.patch.object(ValidateManager, '_is_py_script_or_integration', return_value=True)
        diff_string = "M	Packs/CommonTypes/IncidentFields/incidentfield-Detection_URL.json\n" \
                      "M	Packs/EWS/Classifiers/classifier-EWS_v2.json\n" \
                      "M	Packs/Elasticsearch/Integrations/Elasticsearch_v2/Elasticsearch_v2.py\n" \
                      "M	Packs/Elasticsearch/Integrations/integration-Elasticsearch.yml\n" \
                      "M	Packs/F5/pack_metadata.json\n"\
                      "R100	Packs/EclecticIQ/Integrations/EclecticIQ/EclecticIQ.yml	" \
                      "Packs/EclecticIQ/Integrations/EclecticIQ_new/EclecticIQ_new.yml\n" \
                      "A	Packs/MyNewPack/.pack-ignore\n" \
                      "A	Packs/MyNewPack/.secrets-ignore\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration.py\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration.yml\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration_description.md\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration_image.png\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration_test.py\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/Pipfile\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/Pipfile.lock\n" \
                      "A	Packs/MyNewPack/Integrations/MyNewIntegration/README.md\n" \
                      "A	Packs/MyNewPack/README.md\n" \
                      "A	Packs/MyNewPack/pack_metadata.json\n" \
                      "D	Packs/DeprecatedContent/Scripts/script-ExtractURL.yml"

        validate_manager = ValidateManager()
        modified_files, added_files, deleted_files, old_format_files, changed_meta_files = validate_manager.\
            filter_changed_files(files_string=diff_string, print_ignored_files=True)

        # checking that modified files are recognized correctly
        assert 'Packs/CommonTypes/IncidentFields/incidentfield-Detection_URL.json' in modified_files
        assert 'Packs/EWS/Classifiers/classifier-EWS_v2.json' in modified_files
        assert ('Packs/EclecticIQ/Integrations/EclecticIQ/EclecticIQ.yml',
                'Packs/EclecticIQ/Integrations/EclecticIQ_new/EclecticIQ_new.yml') in modified_files

        # check that the modified code file is not there but the yml file is
        assert 'Packs/Elasticsearch/Integrations/Elasticsearch_v2/Elasticsearch_v2.yml' in modified_files
        assert 'Packs/Elasticsearch/Integrations/Elasticsearch_v2/Elasticsearch_v2.py' not in modified_files

        # check that the modified metadata file is in the changed_meta_files but the added one is not
        assert 'Packs/F5/pack_metadata.json' in changed_meta_files
        assert 'Packs/MyNewPack/pack_metadata.json' not in changed_meta_files

        # check that the added files are recognized correctly
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/README.md' in added_files
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration.yml' in added_files

        # check that the added code files and meta file are not in the added_files
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration.py' not in added_files
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration_test.py' not in added_files
        assert 'Packs/MyNewPack/pack_metadata.json' not in added_files

        # check that non-image, pipfile, description or schema are in the ignored files and the rest are
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/Pipfile' not in validate_manager.ignored_files
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/Pipfile.lock' not in validate_manager.ignored_files
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration_description.md' not \
               in validate_manager.ignored_files
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration_image.png' not \
               in validate_manager.ignored_files
        assert 'Packs/MyNewPack/.secrets-ignore' in validate_manager.ignored_files
        assert 'Packs/MyNewPack/Integrations/MyNewIntegration/MyNewIntegration_test.py' in \
               validate_manager.ignored_files
        assert 'Packs/MyNewPack/.pack-ignore' in validate_manager.ignored_files

        # check recognized old-format file
        assert 'Packs/Elasticsearch/Integrations/integration-Elasticsearch.yml' in old_format_files

        # check recognized deleted file
        assert 'Packs/DeprecatedContent/Scripts/script-ExtractURL.yml' in deleted_files

    def test_setup_git_params(self, mocker):
        mocker.patch.object(ValidateManager, 'get_content_release_identifier', return_value='')

        mocker.patch.object(ValidateManager, 'get_current_working_branch', return_value='20.0.7')
        validate_manager = ValidateManager()
        validate_manager.setup_git_params()

        assert validate_manager.always_valid
        assert validate_manager.compare_type == '..'

        mocker.patch.object(ValidateManager, 'get_current_working_branch', return_value='master')
        # resetting always_valid flag
        validate_manager.always_valid = False
        validate_manager.setup_git_params()
        assert not validate_manager.always_valid
        assert validate_manager.compare_type == '..'

        mocker.patch.object(ValidateManager, 'get_current_working_branch', return_value='not-master-branch')
        validate_manager.setup_git_params()
        assert not validate_manager.always_valid
        assert validate_manager.compare_type == '...'


def test_content_release_identifier_exists():
    """
    When running validate file, it should get a git sha1 from content repo.
    This test assures that if someone changes the .circle/config.yml scheme, it'll fail.
    """
    fv = FilesValidator()
    fv.branch_name = 'master'
    sha1 = fv.get_content_release_identifier()
    assert sha1, 'GIT_SHA1 path in config.yml has been chaged. Fix the demisto-sdk or revert changes in content repo.'
