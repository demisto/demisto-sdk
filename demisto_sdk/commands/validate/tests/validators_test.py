import os
from shutil import copyfile
from typing import Any, Type

import pytest

from demisto_sdk.commands.common.constants import DIR_LIST
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.hook_validations.dashboard import DashboardValidator
from demisto_sdk.commands.common.hook_validations.incident_field import IncidentFieldValidator
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator
from demisto_sdk.commands.common.hook_validations.release_notes import ReleaseNotesValidator
from demisto_sdk.commands.common.hook_validations.reputation import ReputationValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator
from demisto_sdk.commands.common.hook_validations.integration import IntegrationValidator

from demisto_sdk.tests.constants_test import VALID_LAYOUT_PATH, INVALID_LAYOUT_PATH, \
    VALID_REPUTATION_PATH, INVALID_REPUTATION_PATH, VALID_WIDGET_PATH, INVALID_WIDGET_PATH, VALID_DASHBOARD_PATH, \
    VALID_SCRIPT_PATH, INVALID_SCRIPT_PATH, INVALID_DASHBOARD_PATH, VALID_INCIDENT_FIELD_PATH, \
    INVALID_INCIDENT_FIELD_PATH, VALID_INTEGRATION_TEST_PATH, VALID_ONE_LINE_CHANGELOG_PATH, \
    VALID_ONE_LINE_LIST_CHANGELOG_PATH, VALID_MULTI_LINE_CHANGELOG_PATH, VALID_MULTI_LINE_LIST_CHANGELOG_PATH, \
    INVALID_ONE_LINE_1_CHANGELOG_PATH, INVALID_ONE_LINE_2_CHANGELOG_PATH, INVALID_ONE_LINE_LIST_1_CHANGELOG_PATH, \
    INVALID_ONE_LINE_LIST_2_CHANGELOG_PATH, INVALID_MULTI_LINE_1_CHANGELOG_PATH, INVALID_MULTI_LINE_2_CHANGELOG_PATH, \
    LAYOUT_TARGET, WIDGET_TARGET, DASHBOARD_TARGET, INTEGRATION_TARGET, \
    INCIDENT_FIELD_TARGET, SCRIPT_TARGET, SCRIPT_RELEASE_NOTES_TARGET, INTEGRATION_RELEASE_NOTES_TARGET, \
    VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, INVALID_PLAYBOOK_PATH, INVALID_PLAYBOOK_ID_PATH, \
    VALID_INTEGRATION_ID_PATH, INVALID_INTEGRATION_ID_PATH

from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator


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
