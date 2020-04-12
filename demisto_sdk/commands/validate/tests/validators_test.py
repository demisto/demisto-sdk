import json
import os
from shutil import copyfile
from typing import Any, Type

import pytest
from demisto_sdk.commands.common.constants import DIR_LIST
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.dashboard import \
    DashboardValidator
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.incident_field import \
    IncidentFieldValidator
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator
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
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.validate.file_validator import FilesValidator
from demisto_sdk.tests.constants_test import (
    BETA_INTEGRATION_TARGET, DASHBOARD_TARGET, GIT_HAVE_MODIFIED_AND_NEW_FILES,
    INCIDENT_FIELD_TARGET, INCIDENT_TYPE_TARGET,
    INTEGRATION_RELEASE_NOTES_TARGET, INTEGRATION_TARGET,
    INVALID_DASHBOARD_PATH, INVALID_INCIDENT_FIELD_PATH,
    INVALID_INTEGRATION_ID_PATH, INVALID_LAYOUT_PATH,
    INVALID_MULTI_LINE_1_CHANGELOG_PATH, INVALID_MULTI_LINE_2_CHANGELOG_PATH,
    INVALID_NO_HIDDEN_PARAMS, INVALID_ONE_LINE_1_CHANGELOG_PATH,
    INVALID_ONE_LINE_2_CHANGELOG_PATH, INVALID_ONE_LINE_LIST_1_CHANGELOG_PATH,
    INVALID_ONE_LINE_LIST_2_CHANGELOG_PATH, INVALID_PLAYBOOK_CONDITION_1,
    INVALID_PLAYBOOK_CONDITION_2, INVALID_PLAYBOOK_ID_PATH,
    INVALID_PLAYBOOK_PATH, INVALID_PLAYBOOK_PATH_FROM_ROOT,
    INVALID_REPUTATION_PATH, INVALID_SCRIPT_PATH, INVALID_WIDGET_PATH,
    LAYOUT_TARGET, PLAYBOOK_TARGET, REPUTATION_TARGET,
    SCRIPT_RELEASE_NOTES_TARGET, SCRIPT_TARGET, VALID_DASHBOARD_PATH,
    VALID_INCIDENT_FIELD_PATH, VALID_INCIDENT_TYPE_PATH,
    VALID_INTEGRATION_ID_PATH, VALID_INTEGRATION_TEST_PATH, VALID_LAYOUT_PATH,
    VALID_MULTI_LINE_CHANGELOG_PATH, VALID_MULTI_LINE_LIST_CHANGELOG_PATH,
    VALID_NO_HIDDEN_PARAMS, VALID_ONE_LINE_CHANGELOG_PATH,
    VALID_ONE_LINE_LIST_CHANGELOG_PATH, VALID_PLAYBOOK_CONDITION,
    VALID_REPUTATION_PATH, VALID_SCRIPT_PATH, VALID_TEST_PLAYBOOK_PATH,
    VALID_WIDGET_PATH, WIDGET_TARGET)
from mock import patch


class TestValidators:
    CREATED_DIRS = list()

    @classmethod
    def setup_class(cls):
        print("Setups class")
        for dir_to_create in DIR_LIST:
            if not os.path.exists(dir_to_create):
                cls.CREATED_DIRS.append(dir_to_create)
                os.mkdir(dir_to_create)

    @classmethod
    def teardown_class(cls):
        print("Tearing down class")
        for dir_to_delete in cls.CREATED_DIRS:
            if os.path.exists(dir_to_delete):
                os.rmdir(dir_to_delete)

    INPUTS_IS_VALID_VERSION = [
        (VALID_LAYOUT_PATH, LAYOUT_TARGET, True, LayoutValidator),
        (INVALID_LAYOUT_PATH, LAYOUT_TARGET, False, LayoutValidator),
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

    @pytest.mark.parametrize('source, target, answer, validator', INPUTS_IS_VALID_VERSION)
    def test_is_valid_version(self, source, target, answer, validator):
        # type: (str, str, Any, Type[BaseValidator]) -> None
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            validator = validator(structure)
            assert validator.is_valid_version() is answer
        finally:
            os.remove(target)

    INPUTS_is_condition_branches_handled = [
        (INVALID_PLAYBOOK_CONDITION_1, False),
        (INVALID_PLAYBOOK_CONDITION_2, False),
        (VALID_PLAYBOOK_CONDITION, True)
    ]

    @pytest.mark.parametrize('source, answer', INPUTS_is_condition_branches_handled)
    def test_is_condition_branches_handled(self, source, answer):
        # type: (str, str, Any) -> None
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
        # type: (str, str, Any, Type[BaseValidator]) -> None
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            validator = validator(structure)
            assert validator.is_valid_file(validate_rn=False) is answer
        finally:
            os.remove(target)

    INPUTS_RELEASE_NOTES_EXISTS_VALIDATION = [
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, VALID_ONE_LINE_CHANGELOG_PATH, SCRIPT_RELEASE_NOTES_TARGET,
         ReleaseNotesValidator, True),
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, VALID_ONE_LINE_CHANGELOG_PATH, INTEGRATION_RELEASE_NOTES_TARGET,
         ReleaseNotesValidator, False),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET, VALID_ONE_LINE_CHANGELOG_PATH,
         INTEGRATION_RELEASE_NOTES_TARGET, ReleaseNotesValidator, True),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET, VALID_ONE_LINE_CHANGELOG_PATH,
         SCRIPT_RELEASE_NOTES_TARGET, ReleaseNotesValidator, False)
    ]

    @pytest.mark.parametrize('source_dummy, target_dummy, source_release_notes, target_release_notes, '
                             'validator, answer',
                             INPUTS_RELEASE_NOTES_EXISTS_VALIDATION)
    def test_is_release_notes_exists(self, source_dummy, target_dummy,
                                     source_release_notes, target_release_notes, validator, answer, mocker):
        # type: (str, str, str, str, Type[BaseValidator], Any) -> None
        try:
            copyfile(source_dummy, target_dummy)
            copyfile(source_release_notes, target_release_notes)
            mocker.patch.object(ReleaseNotesValidator, 'get_master_diff', side_effect=self.mock_get_master_diff)
            validator = ReleaseNotesValidator(target_dummy)
            assert validator.validate_file_release_notes_exists() is answer
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
                                         SCRIPT_RELEASE_NOTES_TARGET, ReleaseNotesValidator, answer))
                elif file_type == 'Integration':
                    test_package.append((dummy_file, INTEGRATION_TARGET, release_notes_file,
                                         INTEGRATION_RELEASE_NOTES_TARGET, ReleaseNotesValidator, answer))

        return test_package

    test_package = create_release_notes_structure_test_package.__func__()

    @pytest.mark.parametrize('source_dummy, target_dummy, source_release_notes, target_release_notes, '
                             'validator, answer', test_package)
    def test_valid_release_notes_structure(self, source_dummy, target_dummy,
                                           source_release_notes, target_release_notes, validator, answer, mocker):
        # type: (str, str, str, str, Type[BaseValidator], Any) -> None
        try:
            copyfile(source_dummy, target_dummy)
            copyfile(source_release_notes, target_release_notes)
            mocker.patch.object(ReleaseNotesValidator, 'get_master_diff', side_effect=self.mock_get_master_diff)
            validator = ReleaseNotesValidator(target_dummy)
            assert validator.is_valid_release_notes_structure() is answer
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
        # type: (str, str, Any, Type[BaseValidator]) -> None
        try:
            copyfile(str(source), target)
            structure = StructureValidator(str(source))
            validator = validator(structure)
            assert validator.is_id_equals_name() is answer
        finally:
            os.remove(target)

    INPUTS_IS_CONNECTED_TO_ROOT = [
        (INVALID_PLAYBOOK_PATH_FROM_ROOT, False),
        (VALID_TEST_PLAYBOOK_PATH, True)
    ]

    @pytest.mark.parametrize('source, answer', INPUTS_IS_CONNECTED_TO_ROOT)
    def test_is_root_connected_to_all_tasks(self, source, answer):
        # type: (str, str, Any) -> None
        try:
            copyfile(source, PLAYBOOK_TARGET)
            structure = StructureValidator(source)
            validator = PlaybookValidator(structure)
            assert validator.is_root_connected_to_all_tasks() is answer
        finally:
            os.remove(PLAYBOOK_TARGET)

    IS_ALL_PARAMS_NOT_HIDDEN_INPUTS = [
        (VALID_NO_HIDDEN_PARAMS, True),
        (INVALID_NO_HIDDEN_PARAMS, False),
    ]

    @pytest.mark.parametrize("source, answer", IS_ALL_PARAMS_NOT_HIDDEN_INPUTS)
    def test_is_all_params_not_hidden(self, source, answer):
        # type: (str, str) -> None
        structure = StructureValidator(source)
        validator = IntegrationValidator(structure)
        assert validator.is_all_params_not_hidden() is answer

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
        file_validator = FilesValidator(validate_conf_json=False, prev_ver=prev_var)
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
        (VALID_REPUTATION_PATH, REPUTATION_TARGET),
        (VALID_INCIDENT_TYPE_PATH, INCIDENT_TYPE_TARGET),
        (VALID_INTEGRATION_TEST_PATH, BETA_INTEGRATION_TARGET),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_RELEASE_NOTES_TARGET)
    ]

    @pytest.mark.parametrize('source, target', INPUTS_STRUCTURE_VALIDATION)
    def test_is_file_structure(self, source, target):
        # type: (str, str) -> None
        try:
            copyfile(source, target)
            assert FilesValidator(validate_conf_json=False).is_valid_structure()
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
        mocker.patch.object(ReleaseNotesValidator, 'get_master_diff', sreturn_value=None)
        mocker.patch.object(StructureValidator, 'is_valid_file', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_subtype', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_feed', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_description', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_version', return_value=True)
        mocker.patch.object(ImageValidator, 'is_valid', return_value=True)
        mocker.patch.object(DashboardValidator, 'is_id_equals_name', return_value=True)
        mocker.patch.object(ReputationValidator, 'is_id_equals_details', return_value=True)
        mocker.patch.object(IntegrationValidator, 'is_valid_beta', return_value=True)
        file_validator = FilesValidator(validate_conf_json=False)
        file_validator.validate_added_files(file_path, file_type)
        assert file_validator._is_valid

    FILE_PATH = [
        ([VALID_SCRIPT_PATH], 'script')
    ]

    @staticmethod
    def mock_unifier():
        def get_script_package_data_mock(*args, **kwargs):
            return VALID_SCRIPT_PATH, ''
        with patch.object(Unifier, '__init__', lambda a, b: None):
            Unifier.get_script_package_data = get_script_package_data_mock
            return Unifier('')

    @pytest.mark.parametrize('file_path, file_type', FILE_PATH)
    def test_script_valid_rn(self, mocker, file_path, file_type):
        mocker.patch.object(ScriptValidator, 'is_valid_name', return_value=True)
        self.mock_unifier()
        file_validator = FilesValidator(validate_conf_json=False)
        file_validator.validate_added_files(file_path, file_type)
        assert file_validator._is_valid
