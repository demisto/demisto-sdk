import contextlib
import os
import sys
from configparser import ConfigParser
from io import StringIO
from pathlib import Path
from shutil import copyfile
from typing import Any, List, Optional, Union
from unittest.mock import patch

import pytest

import demisto_sdk.commands.validate.old_validate_manager
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    PACKS_PACK_META_FILE_NAME,
    TEST_PLAYBOOK,
    FileType,
)
from demisto_sdk.commands.common.content.content import Content
from demisto_sdk.commands.common.content_constant_paths import CONF_PATH
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.hook_validations.correlation_rule import (
    CorrelationRuleValidator,
)
from demisto_sdk.commands.common.hook_validations.dashboard import DashboardValidator
from demisto_sdk.commands.common.hook_validations.description import (
    DescriptionValidator,
)
from demisto_sdk.commands.common.hook_validations.generic_field import (
    GenericFieldValidator,
)
from demisto_sdk.commands.common.hook_validations.image import ImageValidator
from demisto_sdk.commands.common.hook_validations.incident_field import (
    IncidentFieldValidator,
)
from demisto_sdk.commands.common.hook_validations.integration import (
    IntegrationValidator,
)
from demisto_sdk.commands.common.hook_validations.layout import (
    LayoutsContainerValidator,
    LayoutValidator,
)
from demisto_sdk.commands.common.hook_validations.old_release_notes import (
    OldReleaseNotesValidator,
)
from demisto_sdk.commands.common.hook_validations.pack_unique_files import (
    PackUniqueFilesValidator,
)
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator
from demisto_sdk.commands.common.hook_validations.readme import (
    ReadMeValidator,
)
from demisto_sdk.commands.common.hook_validations.release_notes import (
    ReleaseNotesValidator,
)
from demisto_sdk.commands.common.hook_validations.reputation import ReputationValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.hook_validations.widget import WidgetValidator
from demisto_sdk.commands.common.hook_validations.xsiam_dashboard import (
    XSIAMDashboardValidator,
)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.tests.create_content_graph_test import (
    mock_integration,
    mock_pack,
)
from demisto_sdk.commands.prepare_content.integration_script_unifier import (
    IntegrationScriptUnifier,
)
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
from demisto_sdk.tests.constants_test import (
    CONF_JSON_MOCK_PATH,
    DASHBOARD_TARGET,
    DIR_LIST,
    IGNORED_PNG,
    INCIDENT_FIELD_TARGET,
    INCIDENT_TYPE_TARGET,
    INDICATOR_TYPE_TARGET,
    INTEGRATION_RELEASE_NOTES_TARGET,
    INTEGRATION_TARGET,
    INVALID_BETA_INTEGRATION,
    INVALID_DASHBOARD_PATH,
    INVALID_IGNORED_UNIFIED_INTEGRATION,
    INVALID_INCIDENT_FIELD_PATH,
    INVALID_INTEGRATION_ID_PATH,
    INVALID_INTEGRATION_NO_TESTS,
    INVALID_INTEGRATION_NON_CONFIGURED_TESTS,
    INVALID_LAYOUT_CONTAINER_PATH,
    INVALID_LAYOUT_PATH,
    INVALID_MULTI_LINE_1_CHANGELOG_PATH,
    INVALID_MULTI_LINE_2_CHANGELOG_PATH,
    INVALID_ONE_LINE_1_CHANGELOG_PATH,
    INVALID_ONE_LINE_2_CHANGELOG_PATH,
    INVALID_ONE_LINE_LIST_1_CHANGELOG_PATH,
    INVALID_ONE_LINE_LIST_2_CHANGELOG_PATH,
    INVALID_PLAYBOOK_CONDITION_1,
    INVALID_PLAYBOOK_CONDITION_2,
    INVALID_PLAYBOOK_ID_PATH,
    INVALID_PLAYBOOK_PATH,
    INVALID_PLAYBOOK_PATH_FROM_ROOT,
    INVALID_REPUTATION_PATH,
    INVALID_SCRIPT_PATH,
    INVALID_WIDGET_PATH,
    INVALID_XSIAM_CORRELATION_PATH,
    INVALID_XSIAM_DASHBOARD_PATH,
    LAYOUT_TARGET,
    LAYOUTS_CONTAINER_TARGET,
    MODELING_RULES_SCHEMA_FILE,
    MODELING_RULES_TESTDATA_FILE,
    MODELING_RULES_XIF_FILE,
    MODELING_RULES_YML_FILE,
    PLAYBOOK_TARGET,
    SCRIPT_RELEASE_NOTES_TARGET,
    SCRIPT_TARGET,
    VALID_BETA_INTEGRATION,
    VALID_BETA_PLAYBOOK_PATH,
    VALID_DASHBOARD_PATH,
    VALID_INCIDENT_FIELD_PATH,
    VALID_INCIDENT_TYPE_PATH,
    VALID_INDICATOR_FIELD_PATH,
    VALID_INTEGRATION_ID_PATH,
    VALID_INTEGRATION_TEST_PATH,
    VALID_LAYOUT_CONTAINER_PATH,
    VALID_LAYOUT_PATH,
    VALID_MD,
    VALID_MULTI_LINE_CHANGELOG_PATH,
    VALID_MULTI_LINE_LIST_CHANGELOG_PATH,
    VALID_ONE_LINE_CHANGELOG_PATH,
    VALID_ONE_LINE_LIST_CHANGELOG_PATH,
    VALID_PACK,
    VALID_PACK_IGNORE_PATH,
    VALID_PIPEFILE_LOCK_PATH,
    VALID_PIPEFILE_PATH,
    VALID_PLAYBOOK_CONDITION,
    VALID_REPUTATION_PATH,
    VALID_SCRIPT_PATH,
    VALID_TEST_PLAYBOOK_PATH,
    VALID_WIDGET_PATH,
    VULTURE_WHITELIST_PATH,
    WIDGET_TARGET,
    XSIAM_CORRELATION_TARGET,
    XSIAM_DASHBOARD_TARGET,
)
from demisto_sdk.tests.test_files.validate_integration_test_valid_types import (
    INCIDENT_FIELD,
)
from TestSuite.pack import Pack
from TestSuite.test_tools import (
    ChangeCWD,
)


class MyRepo:
    active_branch = "not-master"

    def remote(self):
        return "remote_path"


@pytest.fixture(autouse=False)
def set_git_test_env(mocker):
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value=True)
    mocker.patch.object(Content, "git_util", return_value=GitUtil())
    mocker.patch.object(
        OldValidateManager, "setup_prev_ver", return_value="origin/master"
    )
    mocker.patch.object(GitUtil, "_is_file_git_ignored", return_value=False)


class TestValidators:
    CREATED_DIRS: List[str] = list()

    @classmethod
    def setup_class(cls):
        for dir_to_create in DIR_LIST:
            if not Path(dir_to_create).exists():
                cls.CREATED_DIRS.append(dir_to_create)
                os.makedirs(dir_to_create)
        copyfile(CONF_JSON_MOCK_PATH, CONF_PATH)

    @classmethod
    def teardown_class(cls):
        Path(CONF_PATH).unlink()
        for dir_to_delete in cls.CREATED_DIRS:
            if Path(dir_to_delete).exists():
                os.rmdir(dir_to_delete)

    INPUTS_IS_VALID_VERSION = [
        (VALID_LAYOUT_PATH, LAYOUT_TARGET, True, LayoutValidator),
        (INVALID_LAYOUT_PATH, LAYOUT_TARGET, False, LayoutValidator),
        (
            VALID_LAYOUT_CONTAINER_PATH,
            LAYOUTS_CONTAINER_TARGET,
            True,
            LayoutsContainerValidator,
        ),
        (
            INVALID_LAYOUT_CONTAINER_PATH,
            LAYOUTS_CONTAINER_TARGET,
            False,
            LayoutsContainerValidator,
        ),
        (VALID_WIDGET_PATH, WIDGET_TARGET, True, WidgetValidator),
        (INVALID_WIDGET_PATH, WIDGET_TARGET, False, WidgetValidator),
        (VALID_DASHBOARD_PATH, DASHBOARD_TARGET, True, DashboardValidator),
        (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
        (
            VALID_INCIDENT_FIELD_PATH,
            INCIDENT_FIELD_TARGET,
            True,
            IncidentFieldValidator,
        ),
        (
            INVALID_INCIDENT_FIELD_PATH,
            INCIDENT_FIELD_TARGET,
            False,
            IncidentFieldValidator,
        ),
        (INVALID_DASHBOARD_PATH, DASHBOARD_TARGET, False, DashboardValidator),
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, True, ScriptValidator),
        (INVALID_SCRIPT_PATH, SCRIPT_TARGET, False, ScriptValidator),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, True, PlaybookValidator),
        (INVALID_PLAYBOOK_PATH, PLAYBOOK_TARGET, False, PlaybookValidator),
    ]

    XSIAM_IS_VALID_FROM_VERSION = [
        (
            INVALID_XSIAM_DASHBOARD_PATH,
            XSIAM_DASHBOARD_TARGET,
            False,
            XSIAMDashboardValidator,
        ),
        (
            INVALID_XSIAM_CORRELATION_PATH,
            XSIAM_CORRELATION_TARGET,
            False,
            CorrelationRuleValidator,
        ),
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
            mocker.patch.object(
                OldReleaseNotesValidator, "get_master_diff", return_value="Comment."
            )
            copyfile(VALID_BETA_PLAYBOOK_PATH, PLAYBOOK_TARGET)
            structure = StructureValidator(
                VALID_BETA_PLAYBOOK_PATH, predefined_scheme="playbook"
            )
            validator = PlaybookValidator(structure)
            mocker.patch.object(validator, "is_script_id_valid", return_value=True)
            assert validator.is_valid_playbook(validate_rn=False)
        finally:
            Path(PLAYBOOK_TARGET).unlink()

    @pytest.mark.parametrize(
        "source, target, answer, validator", (INPUTS_IS_VALID_VERSION)
    )
    def test_is_valid_version(
        self, source: str, target: str, answer: Any, validator: ContentEntityValidator
    ) -> None:
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
            Path(target).unlink()

    @pytest.mark.parametrize(
        "source, target, answer, validator",
        (XSIAM_IS_VALID_FROM_VERSION + INPUTS_IS_VALID_VERSION),
    )
    def test_is_valid_fromversion(
        self, source: str, target: str, answer: Any, validator: ContentEntityValidator
    ) -> None:
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
            Path(target).unlink()

    INPUTS_is_condition_branches_handled = [
        (INVALID_PLAYBOOK_CONDITION_1, False),
        (INVALID_PLAYBOOK_CONDITION_2, False),
        (VALID_PLAYBOOK_CONDITION, True),
    ]

    @pytest.mark.parametrize("source, answer", INPUTS_is_condition_branches_handled)
    def test_is_condition_branches_handled(self, source: str, answer: str) -> None:
        try:
            copyfile(source, PLAYBOOK_TARGET)
            structure = StructureValidator(source)
            validator = PlaybookValidator(structure)
            assert validator.is_condition_branches_handled() is answer
        finally:
            Path(PLAYBOOK_TARGET).unlink()

    INPUTS_is_condition_branches_handled = [
        (INVALID_PLAYBOOK_CONDITION_1, False),
        (INVALID_PLAYBOOK_CONDITION_2, True),
        (VALID_PLAYBOOK_CONDITION, True),
    ]

    @pytest.mark.parametrize("source, answer", INPUTS_is_condition_branches_handled)
    def test_are_default_conditions_valid(self, source: str, answer: str) -> None:
        try:
            copyfile(source, PLAYBOOK_TARGET)
            structure = StructureValidator(source)
            validator = PlaybookValidator(structure)
            assert validator.are_default_conditions_valid() is answer
        finally:
            Path(PLAYBOOK_TARGET).unlink()

    INPUTS_LOCKED_PATHS = [
        (VALID_REPUTATION_PATH, True, ReputationValidator),
        (INVALID_REPUTATION_PATH, False, ReputationValidator),
    ]

    @pytest.mark.parametrize("source, answer, validator", INPUTS_LOCKED_PATHS)
    def test_is_valid_version_locked_paths(self, source, answer, validator):
        """Tests locked path (as reputations.json) so we won't override the file"""
        structure = StructureValidator(source)
        validator = validator(structure)
        assert validator.is_valid_version() is answer

    @pytest.mark.parametrize(
        "source, target, answer, validator",
        (INPUTS_IS_VALID_VERSION + XSIAM_IS_VALID_FROM_VERSION),
    )
    def test_is_file_valid(
        self,
        source: str,
        target: str,
        answer: str,
        validator: Any,
        mocker: ContentEntityValidator,
    ) -> None:
        try:
            copyfile(source, target)
            structure = StructureValidator(source)
            res_validator = validator(structure)
            mocker.patch.object(
                ScriptValidator, "is_valid_script_file_path", return_value=True
            )
            mocker.patch.object(
                ScriptValidator, "is_there_separators_in_names", return_value=True
            )
            mocker.patch.object(
                ScriptValidator, "is_docker_image_valid", return_value=True
            )
            assert res_validator.is_valid_file(validate_rn=False) is answer
        finally:
            Path(target).unlink()

    INPUTS_RELEASE_NOTES_EXISTS_VALIDATION = [
        (
            VALID_SCRIPT_PATH,
            SCRIPT_TARGET,
            VALID_ONE_LINE_CHANGELOG_PATH,
            SCRIPT_RELEASE_NOTES_TARGET,
            OldReleaseNotesValidator,
            True,
        ),
        (
            VALID_SCRIPT_PATH,
            SCRIPT_TARGET,
            VALID_ONE_LINE_CHANGELOG_PATH,
            INTEGRATION_RELEASE_NOTES_TARGET,
            OldReleaseNotesValidator,
            False,
        ),
        (
            VALID_INTEGRATION_TEST_PATH,
            INTEGRATION_TARGET,
            VALID_ONE_LINE_CHANGELOG_PATH,
            INTEGRATION_RELEASE_NOTES_TARGET,
            OldReleaseNotesValidator,
            True,
        ),
        (
            VALID_INTEGRATION_TEST_PATH,
            INTEGRATION_TARGET,
            VALID_ONE_LINE_CHANGELOG_PATH,
            SCRIPT_RELEASE_NOTES_TARGET,
            OldReleaseNotesValidator,
            False,
        ),
    ]

    @pytest.mark.parametrize(
        "source_dummy, target_dummy, source_release_notes, target_release_notes, "
        "validator, answer",
        INPUTS_RELEASE_NOTES_EXISTS_VALIDATION,
    )
    def test_is_release_notes_exists(
        self,
        source_dummy: str,
        target_dummy: str,
        source_release_notes: str,
        target_release_notes: str,
        validator: ContentEntityValidator,
        answer: Any,
        mocker: Any,
    ) -> None:
        try:
            copyfile(source_dummy, target_dummy)
            copyfile(source_release_notes, target_release_notes)
            mocker.patch.object(BaseValidator, "check_file_flags", return_value="")
            mocker.patch.object(
                OldReleaseNotesValidator,
                "get_master_diff",
                side_effect=self.mock_get_master_diff,
            )
            res_validator = OldReleaseNotesValidator(target_dummy)
            assert res_validator.validate_file_release_notes_exists() is answer
        finally:
            Path(target_dummy).unlink()
            Path(target_release_notes).unlink()

    @staticmethod
    def create_release_notes_structure_test_package():
        changelog_needed = [
            (VALID_SCRIPT_PATH, "Script"),
            (VALID_INTEGRATION_TEST_PATH, "Integration"),
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
            (INVALID_MULTI_LINE_2_CHANGELOG_PATH, False),
        ]

        test_package = list()

        for dummy_file, file_type in changelog_needed:
            for release_notes_file, answer in changelog_files_answer:
                if file_type == "Script":
                    test_package.append(
                        (
                            dummy_file,
                            SCRIPT_TARGET,
                            release_notes_file,
                            SCRIPT_RELEASE_NOTES_TARGET,
                            OldReleaseNotesValidator,
                            answer,
                        )
                    )
                elif file_type == "Integration":
                    test_package.append(
                        (
                            dummy_file,
                            INTEGRATION_TARGET,
                            release_notes_file,
                            INTEGRATION_RELEASE_NOTES_TARGET,
                            OldReleaseNotesValidator,
                            answer,
                        )
                    )

        return test_package

    test_package = create_release_notes_structure_test_package.__func__()

    @pytest.mark.parametrize(
        "source_dummy, target_dummy, source_release_notes, target_release_notes, "
        "validator, answer",
        test_package,
    )
    def test_valid_release_notes_structure(
        self,
        source_dummy: str,
        target_dummy: str,
        source_release_notes: str,
        target_release_notes: str,
        validator: ContentEntityValidator,
        answer: Any,
        mocker: Any,
    ) -> None:
        try:
            copyfile(source_dummy, target_dummy)
            copyfile(source_release_notes, target_release_notes)
            mocker.patch.object(BaseValidator, "check_file_flags", return_value="")
            mocker.patch.object(
                OldReleaseNotesValidator,
                "get_master_diff",
                side_effect=self.mock_get_master_diff,
            )
            res_validator = OldReleaseNotesValidator(target_dummy)
            assert res_validator.is_valid_release_notes_structure() is answer
        finally:
            Path(target_dummy).unlink()
            Path(target_release_notes).unlink()

    @staticmethod
    def mock_get_master_diff():
        return "Comment."

    INPUTS_IS_ID_EQUALS_NAME = [
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, True, ScriptValidator),
        (INVALID_SCRIPT_PATH, SCRIPT_TARGET, False, ScriptValidator),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, True, PlaybookValidator),
        (INVALID_PLAYBOOK_ID_PATH, PLAYBOOK_TARGET, False, PlaybookValidator),
        (VALID_INTEGRATION_ID_PATH, INTEGRATION_TARGET, True, IntegrationValidator),
        (INVALID_INTEGRATION_ID_PATH, INTEGRATION_TARGET, False, IntegrationValidator),
    ]

    @pytest.mark.parametrize(
        "source, target, answer, validator", INPUTS_IS_ID_EQUALS_NAME
    )
    def test_is_id_equals_name(
        self,
        source: str,
        target: str,
        answer: Any,
        validator: Union[ScriptValidator, PlaybookValidator, IntegrationValidator],
    ) -> None:
        try:
            copyfile(str(source), target)
            structure = StructureValidator(str(source))
            res_validator = validator(structure)
            assert res_validator.is_id_equals_name() is answer
        finally:
            Path(target).unlink()

    INPUTS_IS_CONNECTED_TO_ROOT = [
        (INVALID_PLAYBOOK_PATH_FROM_ROOT, False),
        (VALID_TEST_PLAYBOOK_PATH, True),
    ]

    @pytest.mark.parametrize("source, answer", INPUTS_IS_CONNECTED_TO_ROOT)
    def test_is_root_connected_to_all_tasks(self, source: str, answer: bool) -> None:
        try:
            copyfile(source, PLAYBOOK_TARGET)
            structure = StructureValidator(source)
            validator = PlaybookValidator(structure)
            assert validator.is_root_connected_to_all_tasks() is answer
        finally:
            Path(PLAYBOOK_TARGET).unlink()

    INPUTS_STRUCTURE_VALIDATION = [
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_TARGET, "integration"),
        (VALID_SCRIPT_PATH, SCRIPT_TARGET, "script"),
        (VALID_DASHBOARD_PATH, DASHBOARD_TARGET, "dashboard"),
        (VALID_INCIDENT_FIELD_PATH, INCIDENT_FIELD_TARGET, "incidentfield"),
        (VALID_TEST_PLAYBOOK_PATH, PLAYBOOK_TARGET, "playbook"),
        (VALID_REPUTATION_PATH, INDICATOR_TYPE_TARGET, "reputation"),
        (VALID_INCIDENT_TYPE_PATH, INCIDENT_TYPE_TARGET, "incidenttype"),
        (VALID_INTEGRATION_TEST_PATH, INTEGRATION_RELEASE_NOTES_TARGET, "integration"),
    ]

    @pytest.mark.parametrize("source, target, file_type", INPUTS_STRUCTURE_VALIDATION)
    def test_is_file_structure(self, source: str, target: str, file_type: str) -> None:
        try:
            copyfile(source, target)
            assert StructureValidator(
                file_path=source, predefined_scheme=file_type
            ).is_valid_file()
        finally:
            Path(target).unlink()

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
        VALID_MD,
    ]

    @pytest.mark.parametrize("file_path", FILES_PATHS_FOR_ALL_VALIDATIONS)
    def test_run_all_validations_on_file(self, mocker, file_path):
        """
        Given
        - A file in packs or beta integration

        When
        - running run_all_validations_on_file on that file

        Then
        -  The file will be validated
        """
        mocker.patch.object(ImageValidator, "is_valid", return_value=True)
        mocker.patch.object(PlaybookValidator, "is_script_id_valid", return_value=True)
        mocker.patch.object(
            ScriptValidator, "is_valid_script_file_path", return_value=True
        )
        mocker.patch.object(
            ScriptValidator, "is_there_separators_in_names", return_value=True
        )
        mocker.patch.object(ScriptValidator, "is_docker_image_valid", return_value=True)
        mocker.patch.object(
            IntegrationValidator, "is_valid_integration_file_path", return_value=True
        )
        mocker.patch.object(
            IntegrationValidator, "is_valid_py_file_names", return_value=True
        )
        mocker.patch.object(
            IntegrationValidator, "is_there_separators_in_names", return_value=True
        )
        mocker.patch.object(
            IntegrationValidator, "is_docker_image_valid", return_value=True
        )
        mocker.patch.object(
            IntegrationValidator,
            "has_no_fromlicense_key_in_contributions_integration",
            return_value=True,
        )
        mocker.patch.object(
            IntegrationValidator, "is_valid_category", return_value=True
        )
        mocker.patch.object(
            DescriptionValidator, "is_valid_description_name", return_value=True
        )
        mocker.patch.object(
            IntegrationValidator, "is_api_token_in_credential_type", return_value=True
        )
        mocker.patch.object(ReadMeValidator, "verify_image_exist", return_value=True)
        mocker.patch.object(OldValidateManager, "is_node_exist", return_value=True)
        validate_manager = OldValidateManager(file_path=file_path, skip_conf_json=True)
        integration_yml = (
            f"{git_path()}/demisto_sdk/tests/test_files/integration-EDL.yml"
        )
        mocker.patch(
            "demisto_sdk.commands.common.hook_validations.readme.get_yml_paths_in_dir",
            return_value=([integration_yml], integration_yml),
        )
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
        INVALID_BETA_INTEGRATION,
    ]

    @pytest.mark.parametrize("file_path", INVALID_FILES_PATHS_FOR_ALL_VALIDATIONS)
    def test_run_all_validations_on_file_failed(
        self, set_git_test_env, mocker, file_path
    ):
        """
        Given
        - An invalid file inside a pack

        When
        - running run_all_validations_on_file on that file

        Then
        -  The file will be validated and failed
        """
        mocker.patch.object(ImageValidator, "is_valid", return_value=True)
        mocker.patch.object(
            IntegrationValidator,
            "has_no_fromlicense_key_in_contributions_integration",
            return_value=True,
        )

        mocker.patch.object(
            IntegrationValidator, "is_api_token_in_credential_type", return_value=True
        )
        mocker.patch.object(
            IntegrationValidator, "is_valid_category", return_value=True
        )
        validate_manager = OldValidateManager(file_path=file_path, skip_conf_json=True)
        assert not validate_manager.run_validation_on_specific_files()

    def test_run_all_validations_on_file_with_modified_id(
        self, set_git_test_env, mocker, integration
    ):
        """
        Given
        - Integration with a modified ID.

        When
        - running 'run_all_validations_on_file' on that file.

        Then
        -  The file will fail validation because its id changed.
        """
        validator = StructureValidator(
            file_path=integration.yml.path, predefined_scheme="integration"
        )
        old = validator.load_data_from_file()
        old["commonfields"]["id"] = "old_id"

        mocker.patch.object(ImageValidator, "is_valid", return_value=True)
        mocker.patch(
            "demisto_sdk.commands.common.hook_validations.structure.is_file_path_in_pack",
            return_value=True,
        )
        mocker.patch(
            "demisto_sdk.commands.common.hook_validations.structure.get_remote_file",
            return_value=old,
        )
        mocker.patch.object(
            IntegrationValidator,
            "has_no_fromlicense_key_in_contributions_integration",
            return_value=True,
        )
        mocker.patch.object(
            IntegrationValidator, "is_api_token_in_credential_type", return_value=True
        )
        mocker.patch.object(
            IntegrationValidator, "is_valid_category", return_value=True
        )
        with ChangeCWD(integration.repo_path):
            validate_manager = OldValidateManager(skip_conf_json=True)
            assert not validate_manager.run_validations_on_file(
                file_path=integration.yml.path,
                pack_error_ignore_list=[],
                is_modified=True,
            )

    def test_files_validator_validate_pack_unique_files(self, mocker):
        from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack

        mocker.patch.object(
            tools, "get_dict_from_file", return_value=({"approved_list": {}}, "json")
        )
        mocker.patch.object(Pack, "should_be_deprecated", return_value=False)
        # mocking should_be_deprecated must be done because the get_dict_from_file is being mocked.
        # should_be_deprecated relies on finding the correct file content from get_dict_from_file function.
        validate_manager = OldValidateManager(skip_conf_json=True)
        result = validate_manager.validate_pack_unique_files(
            VALID_PACK, pack_error_ignore_list={}
        )
        assert result

    def test_files_validator_missing_meta_file(self, repo, caplog, monkeypatch):
        """
        Given
            A path of a pack folder
        When
            Running  validate_pack_unique_files
        Then
            Ensure required_pack_file_does_not_exist fails if and only if PACKS_PACK_META_FILE_NAME doesn't exist
        """
        pack = repo.create_pack("pack")
        validate_manager = OldValidateManager(skip_conf_json=True)
        err_msg, err_code = Errors.required_pack_file_does_not_exist(
            PACKS_PACK_META_FILE_NAME
        )

        validate_manager.validate_pack_unique_files(
            str(pack.path), pack_error_ignore_list={}
        )
        assert err_msg not in caplog.text
        assert err_code not in caplog.text

        Path(pack.pack_metadata.path).unlink()
        validate_manager.validate_pack_unique_files(
            str(pack.path), pack_error_ignore_list={}
        )
        assert err_msg in caplog.text

    def test_validate_pack_dependencies(self, mocker):
        """
        Given:
            - A file path with valid pack dependencies
        When:
            - checking validity of pack dependencies for added or modified files
        Then:
            - return a True validation response
        """
        from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack

        id_set_path = os.path.normpath(
            os.path.join(
                __file__,
                git_path(),
                "demisto_sdk",
                "tests",
                "test_files",
                "id_set",
                "id_set.json",
            )
        )
        mocker.patch.object(
            tools, "get_dict_from_file", return_value=({"approved_list": {}}, "json")
        )
        mocker.patch.object(Pack, "should_be_deprecated", return_value=False)
        # mocking should_be_deprecated must be done because the get_dict_from_file is being mocked.
        # should_be_deprecated relies on finding the correct file type from get_dict_from_file function.

        validate_manager = OldValidateManager(
            skip_conf_json=True, id_set_path=id_set_path
        )
        result = validate_manager.validate_pack_unique_files(
            VALID_PACK, pack_error_ignore_list={}
        )
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
            os.path.join(
                __file__,
                git_path(),
                "demisto_sdk",
                "tests",
                "test_files",
                "id_set",
                "id_set.json",
            )
        )
        validate_manager = OldValidateManager(
            skip_conf_json=True, id_set_path=id_set_path
        )
        mocker.patch.object(
            PackUniqueFilesValidator,
            "validate_pack_readme_and_pack_description",
            return_value=True,
        )
        mocker.patch.object(
            PackUniqueFilesValidator, "_read_metadata_content", return_value=dict()
        )
        result = validate_manager.validate_pack_unique_files(
            "QRadar", pack_error_ignore_list={}
        )
        assert not result

    @staticmethod
    def mock_unifier():
        def get_script_or_integration_package_data_mock(*args, **kwargs):
            return VALID_SCRIPT_PATH, ""

        with patch.object(IntegrationScriptUnifier, "__init__", lambda a, b: None):
            patch.object(
                IntegrationScriptUnifier,
                "get_script_or_integration_package_data",
                return_value=get_script_or_integration_package_data_mock,
            )
            return IntegrationScriptUnifier("")

    def test_script_valid_rn(self, mocker):
        """
        Given:
            - A valid script path
        When:
            - checking validity of added files
        Then:
            - return a True validation response
        """
        mocker.patch.object(ScriptValidator, "is_valid_name", return_value=True)
        mocker.patch.object(
            ScriptValidator, "is_valid_script_file_path", return_value=True
        )
        mocker.patch.object(
            ScriptValidator, "is_there_separators_in_names", return_value=True
        )
        mocker.patch.object(ScriptValidator, "is_docker_image_valid", return_value=True)

        self.mock_unifier()
        validate_manager = OldValidateManager(skip_conf_json=True)
        is_valid = validate_manager.validate_added_files([VALID_SCRIPT_PATH], None)
        assert is_valid

    def test_pack_validation(self, mocker):
        mocker.patch.object(OldValidateManager, "is_node_exist", return_value=True)
        validate_manager = OldValidateManager(file_path=VALID_PACK, skip_conf_json=True)
        is_valid = validate_manager.run_validation_on_package(VALID_PACK, None)
        assert is_valid

    VALID_ADDED_RELEASE_NOTES = {
        "Packs/HelloWorld/ReleaseNotes/1_2_0.md",
        "Packs/ThreatIntelligenceManagement/ReleaseNotes/1_1_0.md"
        "Packs/Tanium/ReleaseNotes/1_1_0.md",
    }
    INVALID_ADDED_RELEASE_NOTES = {
        "Packs/HelloWorld/ReleaseNotes/1_2_0.md",
        "Packs/HelloWorld/ReleaseNotes/1_3_0.md",
        "Packs/ThreatIntelligenceManagement/ReleaseNotes/1_1_0.md"
        "Packs/Tanium/ReleaseNotes/1_1_0.md",
    }
    VERIFY_NO_DUP_RN_INPUT = [
        (VALID_ADDED_RELEASE_NOTES, True),
        (INVALID_ADDED_RELEASE_NOTES, False),
    ]

    @pytest.mark.parametrize("added_files, expected", VERIFY_NO_DUP_RN_INPUT)
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
        validate_manager = OldValidateManager(skip_conf_json=True)
        result = validate_manager.validate_no_duplicated_release_notes(added_files)
        assert result is expected

    @pytest.mark.parametrize(
        "file_path, file_type, expected", [(TEST_PLAYBOOK, "testplaybook", False)]
    )
    def test_are_tests_configured_testplaybook(
        self, file_path: str, file_type: str, expected: bool
    ):
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

    ARE_TEST_CONFIGURED_TEST_INPUT = [
        pytest.param(
            {"tests": ["PagerDuty Test"]}, "PagerDuty v2", True, id="well configured"
        ),
        pytest.param(
            {}, "PagerDuty v3", False, id="tests section missing from yml and conf.json"
        ),
        pytest.param(
            {},
            "PagerDuty v2",
            True,
            id="tests section missing from yml but in conf.json",
        ),
        pytest.param(
            {"tests": ["Non configured test"]},
            "PagerDuty v4",
            False,
            id="integration id is not in conf.json",
        ),
        pytest.param(
            {"tests": ["PagerDuty Test", "Non configured test"]},
            "PagerDuty v2",
            False,
            id="only some of the tests are in conf.json",
        ),
        pytest.param(
            {"tests": ["Non configured test"]},
            "PagerDuty v2",
            False,
            id="yml tests mismatch conf.json tests",
        ),
    ]

    @pytest.mark.parametrize(
        "configured_tests, integration_id, expected", ARE_TEST_CONFIGURED_TEST_INPUT
    )
    def test_are_tests_configured_integration(
        self, repo, integration_id, configured_tests: str, expected: bool
    ):
        """
        Given
        - A content item

        When
        - Checking if the item has tests configured

        Then
        -  validator return the correct answer accordingly
        """

        with ChangeCWD(repo.path):
            pack = repo.create_pack("Pack")
            yml_dict = {"commonfields": {"id": integration_id}}
            yml_dict.update(configured_tests)
            integration = pack.create_integration(name=integration_id, yml=yml_dict)
            repo.conf.write_json(
                tests=[{"integrations": "PagerDuty v2", "playbookID": "PagerDuty Test"}]
            )
            integration_yml_path = os.path.join(
                integration.path, integration.name + ".yml"
            )
            structure_validator = StructureValidator(
                integration_yml_path, predefined_scheme="integration"
            )
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
        validate_manager = OldValidateManager()
        assert validate_manager.run_validations_on_file(
            INVALID_IGNORED_UNIFIED_INTEGRATION, None
        )

    @pytest.mark.parametrize(
        "file_type, path_to_file",
        [
            (FileType.CHANGELOG, VALID_ONE_LINE_CHANGELOG_PATH),
            (FileType.DOC_IMAGE, "image.png"),
            (
                FileType.MODELING_RULE_SCHEMA,
                "Packs/some/ModelingRules/Some/Some_schema.json",
            ),
            (
                FileType.XSIAM_REPORT_IMAGE,
                "Packs/XSIAMPack/XSIAMReports/XSIAM_Some_Report.json",
            ),
            (FileType.PIPFILE, VALID_PIPEFILE_PATH),
            (FileType.PIPFILE_LOCK, VALID_PIPEFILE_LOCK_PATH),
            (FileType.TXT, "txt_file.txt"),
            (FileType.JAVASCRIPT_FILE, "java_script_file.js"),
            (FileType.POWERSHELL_FILE, "powershell_file.ps1"),
            (FileType.PYLINTRC, ".pylintrc"),
            (FileType.SECRET_IGNORE, ".secrets-ignore"),
            (FileType.LICENSE, "LICENSE"),
            (FileType.UNIFIED_YML, "Packs/DummyPack/Scripts/DummyScript_unified.yml"),
            (FileType.PACK_IGNORE, VALID_PACK_IGNORE_PATH),
            (FileType.INI, "ini_file.ini"),
            (FileType.PEM, "pem_file.pem"),
            (FileType.METADATA, ".pack_metadata.json"),
            (FileType.VULTURE_WHITELIST, VULTURE_WHITELIST_PATH),
        ],
    )
    def test_skipped_file_types(self, mocker, file_type, path_to_file):
        """
        Given:
            - A file of a type that should be skipped
        When:
            - Validating the file
        Then:
            - The file should be skipped
        """

        mocker.patch.object(
            demisto_sdk.commands.common.tools,
            "find_type",
            return_value=file_type,
        )

        validate_manager = OldValidateManager()
        assert validate_manager.run_validations_on_file(path_to_file, None)
        assert path_to_file in validate_manager.ignored_files

    def test_non_integration_png_files_ignored(self, set_git_test_env):
        """
        Given
        - A png file
        When
        - Validating it
        Then
        -  validator should ignore those files and return False
        """
        validate_manager = OldValidateManager()
        assert validate_manager.run_validations_on_file(IGNORED_PNG, None) is False

    def test_get_error_ignore_list(self, mocker):
        """
        Given:
            - A file path to pack ignore
        When:
            - running get_error_ignore_list from validate manager
        Then:
            - verify that the created ignored_errors list is being created with all of the
            error codes that is in the .pack-ignore, also the error codes which cannot be ignored.
        """
        files_path = os.path.normpath(
            os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files")
        )
        test_file = os.path.join(files_path, "fake_pack/.pack-ignore")

        mocker.patch.object(
            demisto_sdk.commands.validate.old_validate_manager.tools,
            "get_pack_ignore_file_path",
            return_value=test_file,
        )

        validate_manager = OldValidateManager()
        ignore_errors_list = validate_manager.get_error_ignore_list("fake")
        assert ignore_errors_list["file_name"] == [
            "BA101",
            "SC101",
            "BA106",
        ]
        assert "SC100" not in ignore_errors_list["file_name"]

    def test_create_ignored_errors_list(self):
        """
        Given:
            - A list of errors we want to exclude from the all errors list.
        When:
            - Running create_ignored_errors_list from validate manager.
        Then:
            - verify that the error list that comes out has a correct sublist.
        """
        validate_manager = OldValidateManager()
        errors_to_exclude = [
            "IN",
            "SC",
            "CJ",
            "DA",
            "DB",
            "DO",
            "ID",
            "DS",
            "IM",
            "IF",
            "IT",
            "RN",
            "RM",
            "PA",
            "PB",
            "WD",
            "RP",
            "BA100",
            "BC100",
            "ST",
            "CL",
            "MP",
            "LO",
            "XC",
            "GF",
            "PP",
            "JB",
            "LI100",
            "LI101",
        ]
        error_list = validate_manager.create_ignored_errors_list(errors_to_exclude)
        assert {
            "BA101",
            "BA102",
            "BA103",
            "BA104",
            "BA105",
            "BA106",
            "BA107",
            "BA108",
            "BA109",
            "BA110",
            "BA111",
            "BA112",
            "BA113",
            "BA114",
            "BA115",
            "BC101",
            "BC102",
            "BC103",
            "BC104",
        }.issubset(error_list)

    def test_added_files_type_using_function(self, set_git_test_env, repo, mocker):
        """
        Given:
            - A list of errors that should be checked
        When:
            - Running create_ignored_errors_list from validate manager
        Then:
            - verify that the ignored error list that comes out is correct
        """

        mocker.patch.object(BaseValidator, "check_file_flags", return_value="")
        saved_stdout = sys.stdout
        pack = repo.create_pack("pack")
        pack.create_test_script()
        with ChangeCWD(pack.repo_path):
            os.system(
                "mv Packs/pack/Scripts/sample_script/sample_script.yml Packs/pack/TestPlaybooks/"
            )
            x = OldValidateManager()
            try:
                out = StringIO()
                sys.stdout = out

                x.validate_added_files(
                    {"Packs/pack/TestPlaybooks/sample_script.yml"}, None
                )
                assert "Missing id in root" not in out.getvalue()
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
            os.path.join(
                __file__, f"{git_path()}/demisto_sdk/tests", "test_files", "Packs"
            )
        )
        test_file = os.path.join(
            files_path,
            "CortexXDR",
            "Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml",
        )
        validate_manager = OldValidateManager()
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
            os.path.join(__file__, f"{git_path()}/demisto_sdk/tests", "test_files")
        )
        test_file = os.path.join(
            files_path,
            "UnifiedIntegrations/Integrations/integration-Symantec_Messaging_Gateway.yml",
        )
        validate_manager = OldValidateManager()
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
        pack1 = repo.create_pack("PackName1")
        incident_field1 = pack1.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        pack2 = repo.create_pack("PackName2")
        incident_field2 = pack2.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        validate_manager = OldValidateManager()
        pack3 = repo.create_pack("PackName3")
        incident_field3 = pack3.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )

        modified_files = {
            incident_field1.get_path_from_pack(),
            incident_field2.get_path_from_pack(),
        }
        old_format_files = {incident_field3.get_path_from_pack()}
        added_files = {
            "Packs/PackName1/ReleaseNotes/1_0_0.md",
            "Packs/PackName2/ReleaseNotes/1_1_1.md",
            "Packs/PackName3/ReleaseNotes/1_1_1.md",
        }

        with ChangeCWD(repo.path):
            assert (
                validate_manager.validate_no_missing_release_notes(
                    modified_files=modified_files,
                    old_format_files=old_format_files,
                    added_files=added_files,
                    graph_validator=None,
                )
                is True
            )

    def test_validate_no_missing_release_notes__missing_rn_in_modified_files(
        self, repo, mocker
    ):
        """
        Given:
            - 2 packs with modified files and release notes for only one and no old format files
        When:
            - running validate_no_missing_release_notes on the files
        Then:
            - return a False as there are release notes missing
        """
        mocker.patch.object(
            BaseValidator, "update_checked_flags_by_support_level", return_value=""
        )
        pack1 = repo.create_pack("PackName1")
        incident_field1 = pack1.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        pack2 = repo.create_pack("PackName2")
        incident_field2 = pack2.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        validate_manager = OldValidateManager()
        modified_files = {
            incident_field1.get_path_from_pack(),
            incident_field2.get_path_from_pack(),
        }
        # Mock the graph and the get_api_module_dependencies_from_graph function
        integration_mock = mock_integration("ApiDependent")
        mocker.patch(
            "demisto_sdk.commands.validate.old_validate_manager.get_api_module_dependencies_from_graph",
            return_value=[integration_mock],
        )
        added_files = {"Packs/PackName1/ReleaseNotes/1_0_0.md"}
        with ChangeCWD(repo.path):
            assert (
                validate_manager.validate_no_missing_release_notes(
                    modified_files=modified_files,
                    old_format_files=set(),
                    added_files=added_files,
                    graph_validator=mocker.MagicMock(),
                )
                is False
            )

    def test_validate_no_missing_release_notes__missing_rn_dependent_on_api_module(
        self, repo, mocker, tmpdir
    ):
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
        pack1 = repo.create_pack("ApiModules")
        api_script1 = pack1.create_script("APIScript")
        api_script1.create_default_script(name="APIScript")
        integration_mock = mock_integration("ApiDependent", "Packs/ApiDependent/")
        validate_manager = OldValidateManager()
        mocker.patch(
            "demisto_sdk.commands.validate.old_validate_manager.get_api_module_dependencies_from_graph",
            return_value=[integration_mock],
        )
        mocker.patch.object(
            BaseValidator, "update_checked_flags_by_support_level", return_value=""
        )

        validate_manager = OldValidateManager()
        modified_files = {api_script1.yml.rel_path}
        added_files = {"Packs/ApiModules/ReleaseNotes/1_0_0.md"}
        with ChangeCWD(repo.path):
            assert (
                validate_manager.validate_no_missing_release_notes(
                    modified_files=modified_files,
                    old_format_files=set(),
                    added_files=added_files,
                    graph_validator=mocker.MagicMock(),
                )
                is False
            )

    def test_validate_no_missing_release_notes__happy_rn_dependent_on_api_module(
        self, repo, mocker, tmpdir
    ):
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
        from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

        mocker.patch.object(
            BaseValidator, "update_checked_flags_by_support_level", return_value=""
        )
        pack1 = repo.create_pack("ApiModules")
        api_script1 = pack1.create_script("APIScript")
        validate_manager = OldValidateManager()
        modified_files = {api_script1.yml.rel_path}
        added_files = {
            "Packs/ApiModules/ReleaseNotes/1_0_0.md",
            "Packs/ApiDependent/ReleaseNotes/1_0_0.md",
        }
        integration_mock = mock_integration("ApiDependent")
        mocker.patch(
            "demisto_sdk.commands.validate.old_validate_manager.get_api_module_dependencies_from_graph",
            return_value=[integration_mock],
        )

        mocker.patch.object(
            ContentItem,
            "in_pack",
            mock_pack("ApiDependent", path=Path("Packs/ApiDependent")),
        )
        with ChangeCWD(repo.path):
            assert (
                validate_manager.validate_no_missing_release_notes(
                    modified_files=modified_files,
                    old_format_files=set(),
                    added_files=added_files,
                    graph_validator=mocker.MagicMock(),
                )
                is True
            )

    def test_validate_no_missing_release_notes__missing_rn_in_old_format_files(
        self, repo, mocker
    ):
        """
        Given:
            - 2 packs one modified files the other an old format file and release notes for only one
        When:
            - running validate_no_missing_release_notes on the files
        Then:
            - return a False as there are release notes missing
        """
        mocker.patch.object(
            BaseValidator, "update_checked_flags_by_support_level", return_value=""
        )
        pack1 = repo.create_pack("PackName1")
        incident_field1 = pack1.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        pack2 = repo.create_pack("PackName2")
        incident_field2 = pack2.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        validate_manager = OldValidateManager()
        modified_files = {incident_field1.get_path_from_pack()}
        added_files = {"Packs/PackName1/ReleaseNotes/1_0_0.md"}
        old_format_files = {incident_field2.get_path_from_pack()}
        with ChangeCWD(repo.path):
            assert (
                validate_manager.validate_no_missing_release_notes(
                    modified_files=modified_files,
                    old_format_files=old_format_files,
                    added_files=added_files,
                    graph_validator=mocker.MagicMock(),
                )
                is False
            )

    def test_validate_no_missing_release_notes__missing_rn_for_added_file_in_existing_pack(
        self, repo, mocker
    ):
        """
        Given:
            - an existing pack with an added file which does not have release notes
        When:
            - running validate_no_missing_release_notes on the files
        Then:
            - return a False as there are release notes missing
        """
        mocker.patch.object(
            BaseValidator, "update_checked_flags_by_support_level", return_value=""
        )
        pack1 = repo.create_pack("PackName1")
        incident_field1 = pack1.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        validate_manager = OldValidateManager()
        added_files = {incident_field1.get_path_from_pack()}
        with ChangeCWD(repo.path):
            assert (
                validate_manager.validate_no_missing_release_notes(
                    modified_files=set(),
                    old_format_files=set(),
                    added_files=added_files,
                    graph_validator=mocker.MagicMock(),
                )
                is False
            )

    def test_validate_no_missing_release_notes__no_missing_rn_new_pack(
        self, repo, mocker
    ):
        """
        Given:
            - an added file in a new pack
        When:
            - running validate_no_missing_release_notes on the files
        Then:
            - return a True as there are no release notes missing
        """
        mocker.patch.object(
            BaseValidator, "update_checked_flags_by_support_level", return_value=""
        )
        pack1 = repo.create_pack("PackName1")
        incident_field1 = pack1.create_incident_field(
            "incident-field", content=INCIDENT_FIELD
        )
        validate_manager = OldValidateManager()
        validate_manager.new_packs = {"PackName1"}
        added_files = {incident_field1.get_path_from_pack()}
        with ChangeCWD(repo.path):
            assert (
                validate_manager.validate_no_missing_release_notes(
                    modified_files=set(),
                    old_format_files=set(),
                    added_files=added_files,
                    graph_validator=mocker.MagicMock(),
                )
                is True
            )

    def test_validate_no_old_format__with_toversion(self):
        """
        Given:
            - an old format_file with toversion
        When:
            - running validate_no_old_format on the file
        Then:
            - return a True as the file is valid
        """
        validate_manager = OldValidateManager()
        old_format_files = {
            f"{git_path()}/demisto_sdk/tests/test_files/Unifier/SampleScriptPackage/"
            "script-SampleScriptPackageSanityDocker45_45.yml"
        }
        assert validate_manager.validate_no_old_format(old_format_files)

    def test_validate_no_old_format__without_toversion(self, mocker):
        """
        Given:
            - 2 old format_file without toversion
        When:
            - running validate_no_old_format on the files
        Then:
            - return a False as the files are invalid
            - assert the handle_error function is called for each file
        """
        handle_error_mock = mocker.patch.object(
            BaseValidator, "handle_error", return_value="not-a-non-string"
        )
        # silence_init_prints=True to avoid printing the id_set.json not found error
        validate_manager = OldValidateManager(silence_init_prints=True)
        old_format_files = {
            f"{git_path()}/demisto_sdk/tests/test_files/script-valid.yml",
            f"{git_path()}/demisto_sdk/tests/test_files/integration-test.yml",
        }
        assert not validate_manager.validate_no_old_format(old_format_files)
        assert handle_error_mock.call_count == 2

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
        with ChangeCWD(repo.path):
            validate_manager = OldValidateManager()
            pack1 = repo.create_pack("Pack1")
            script = pack1.create_script("Script1")
            script2 = pack1.create_script("Script2")
            script3 = pack1.create_script("Script3")
            script.yml.write_dict(
                {
                    "script": "\n\n\ndef main():\n    return_error('Not implemented.')\n\u200b\n"
                    "if __name__\\ in ('builtins', '__builtin__', '__main__'):\n    main()\n",
                    "deprecated": True,
                }
            )
            script2.yml.write_dict(
                {
                    "script": "\n\n\ndef main():\n    return_error('Not implemented.')\n\u200b\n"
                    "if __name__\\ in ('builtins', '__builtin__', '__main__'):\n    main()\n",
                    "deprecated": False,
                }
            )
            script3.yml.write_dict(
                {
                    "script": "\n\n\ndef main():\n    return_error('Not implemented.')\n\u200b\n"
                    "if __name__\\ in ('builtins', '__builtin__', '__main__'):\n    main()\n"
                }
            )
            old_format_file = {script.yml.path}
            deprecated_false_file = {script2.yml.path, script3.yml.path}
            assert validate_manager.validate_no_old_format(old_format_file)
            assert not validate_manager.validate_no_old_format(deprecated_false_file)

    def test_setup_git_params_master_branch(self, mocker):
        mocker.patch.object(
            GitUtil, "get_current_working_branch", return_value="master"
        )
        validate_manager = OldValidateManager()
        validate_manager.setup_git_params()

        assert not validate_manager.always_valid
        assert validate_manager.skip_pack_rn_validation

    def test_setup_git_params_non_master_branch(self, mocker):
        mocker.patch.object(
            GitUtil, "get_current_working_branch", return_value="not-master-branch"
        )
        validate_manager = OldValidateManager()
        validate_manager.setup_git_params()

        assert not validate_manager.always_valid
        assert not validate_manager.skip_pack_rn_validation

    def test_get_packs(self):
        modified_files = {
            "Packs/CortexXDR/Integrations/XDR_iocs/XDR_iocs.py",
            "Packs/Claroty/Integrations/Claroty/Claroty.py",
            "Packs/McAfee_ESM/Integrations/McAfee_ESM_v2/McAfee_ESM_v2.yml",
            "Packs/Malware/IncidentTypes/incidenttype-Malware.json",
            "Packs/Claroty/Layouts/layoutscontainer-Claroty_Integrity_Incident.json",
        }
        packs = {"CortexXDR", "Claroty", "McAfee_ESM", "Malware"}
        validate_manager = OldValidateManager(
            skip_conf_json=True, check_is_unskipped=False
        )
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
        file_path = "Packs/CortexXDR/ReleaseNotes/1_1_1.md"
        modified_files = {
            "Packs/CortexXDR/Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml"
        }
        mocker.patch.object(ReleaseNotesValidator, "__init__", return_value=None)
        mocker.patch.object(ReleaseNotesValidator, "is_file_valid", return_value=True)
        validate_manager = OldValidateManager(skip_conf_json=True)
        assert validate_manager.validate_release_notes(
            file_path, {}, modified_files, None
        )

    def test_validate_release_notes__invalid_rn_for_new_pack(self, mocker):
        """
        Given
            - A release note file for a newly created pack.
        When
            - Run the validate command.
        Then
            - validate_release_notes returns False
        """

        file_path = "Packs/CortexXDR/ReleaseNotes/1_0_0.md"
        modified_files = {
            "Packs/CortexXDR/Integrations/PaloAltoNetworks_XDR/PaloAltoNetworks_XDR.yml"
        }
        mocker.patch.object(ReleaseNotesValidator, "__init__", return_value=None)
        mocker.patch.object(ReleaseNotesValidator, "is_file_valid", return_value=True)
        mocker.patch.object(
            BaseValidator,
            "handle_error",
            return_value="ReleaseNotes for newly created pack",
        )
        validate_manager = OldValidateManager(skip_conf_json=True)
        validate_manager.new_packs = {"CortexXDR"}
        assert (
            validate_manager.validate_release_notes(
                file_path, {file_path}, modified_files, None
            )
            is False
        )

    def test_run_validations_on_file_release_notes_config(self, pack):
        """
        Sanity test for running validation on RN config file

        Given:
        - Valid RN config file.

        When:
        - Checking if file is valid.

        Then:
        - Ensure true is returned.
        """
        rn = pack.create_release_notes("1_0_1", is_bc=True)
        rn_config_path: str = str(rn.path).replace("md", "json")
        with ChangeCWD(pack.repo_path):
            validate_manager: OldValidateManager = OldValidateManager()
            assert validate_manager.run_validations_on_file(rn_config_path, list())

    @pytest.mark.parametrize(
        "answer, integration_id", [(True, "MyIntegration"), (False, "MyIntegration  ")]
    )
    def test_is_there_spaces_in_the_end_of_id_yml(
        self, pack: Pack, answer, integration_id
    ):
        """
        Given
            - An integration which id doesn't ends with whitespaces
            - An integration which id ends with spaces
        When
            - Run the validate command.
        Then
            - validate that is_there_spaces_in_the_end_of_id returns expected answer
        """
        integration = pack.create_integration("MyIntegration")
        integration.yml.write_dict({"commonfields": {"id": integration_id}})
        structure = StructureValidator(integration.yml.path)
        res_validator = IntegrationValidator(structure)
        assert res_validator.is_there_spaces_in_the_end_of_id() is answer

    @pytest.mark.parametrize(
        "answer, dashboard_id", [(True, "MyDashboard"), (False, "MyDashboard  ")]
    )
    def test_is_there_spaces_in_the_end_of_id_json(
        self, pack: Pack, answer, dashboard_id
    ):
        """
        Given
            - A dashboard which id doesn't ends with whitespaces
            - A dashboard which id ends with spaces
        When
            - Run the validate command.
        Then
            - validate that is_there_spaces_in_the_end_of_id returns expected answer
        """
        dashboard = pack.create_dashboard("MyDashboard")
        dashboard.write_json({"id": dashboard_id})
        structure = StructureValidator(dashboard.path)
        res_validator = DashboardValidator(structure)
        assert res_validator.is_there_spaces_in_the_end_of_id() is answer

    @pytest.mark.parametrize(
        "answer, dashboard_name", [(True, "MyDashboard"), (False, "MyDashboard  ")]
    )
    def test_is_there_spaces_in_the_end_of_name(
        self, pack: Pack, answer, dashboard_name
    ):
        """
        Given
            - A dashboard which name doesn't ends with whitespaces
            - A dashboard which name ends with spaces
        When
            - Run the validate command.
        Then
            - validate that is_there_spaces_in_the_end_of_name returns expected answer
        """
        dashboard = pack.create_dashboard(dashboard_name)
        dashboard.write_json({"name": dashboard_name})
        structure = StructureValidator(dashboard.path)
        res_validator = IntegrationValidator(structure)
        assert res_validator.is_there_spaces_in_the_end_of_name() is answer

    @pytest.mark.parametrize(
        "file_path",
        [
            "Packs/SomeIntegration/IntegrationName/file.py",
            "Packs/pack_id/Integrations/integration_id/file.yml",
        ],
    )
    def test_ignore_files_irrelevant_for_validation_should_not_ignore(
        self, file_path: str
    ):
        """
        Given
            - File path
        When
            - File should not be ignored
        Then
            - File is not ignored and False is returned
        """
        validate_manager = OldValidateManager(check_is_unskipped=False)
        assert not validate_manager.ignore_files_irrelevant_for_validation(file_path)

    @pytest.mark.parametrize(
        "file_path",
        [
            "Packs/pack_id/Integrations/integration_id/test_data/file.json",
            "Packs/pack_id/test_data/file.json",
            "Packs/pack_id/Scripts/script_id/test_data/file.json",
            "Packs/pack_id/TestPlaybooks/test_data/file.json",
            "Packs/pack_id/Integrations/integration_id/command_examples.txt",
            "Packs/pack_id/Integrations/integration_id/test.txt",
            "Packs/pack_id/.secrets-ignore",
        ],
    )
    def test_ignore_files_irrelevant_for_validation_test_file(self, file_path: str):
        """
        Given
            - File path
        When
            - File is irrelevant for validation
        Then
            - File is ignored and True is returned
        """
        validate_manager = OldValidateManager(check_is_unskipped=False)
        assert validate_manager.ignore_files_irrelevant_for_validation(file_path)

    @pytest.mark.parametrize(
        "file_path",
        [
            "OtherDir/Integration/file.json",
            "TestData/file.json",
            "TestPlaybooks/file.yml",
            "docs/dbot/README.md",
        ],
    )
    def test_ignore_files_irrelevant_for_validation_non_pack(self, file_path: str):
        """
        Given
            - File path
        When
            - File is not part of the Packs directory
        Then
            - File is ignored and True is returned
        """
        validate_manager = OldValidateManager(check_is_unskipped=False)
        assert validate_manager.ignore_files_irrelevant_for_validation(file_path)

    @pytest.mark.parametrize(
        "expected_result, unsearchable", [(True, True), (False, False)]
    )
    def test_is_valid_unsearchable_key_incident_field(
        self, pack: Pack, expected_result, unsearchable
    ):
        """
        Given
            - An incident field which unsearchable is true
            - An incident field which unsearchable is false
        When
            - Run the validate command.
        Then
            - validate that is_valid_unsearchable_key expected answer
        """
        incident_field = pack.create_incident_field("MyIncidentField")
        incident_field.update({"unsearchable": unsearchable})
        structure = StructureValidator(incident_field.path)
        res_validator = IncidentFieldValidator(structure)
        assert res_validator.is_valid_unsearchable_key() is expected_result

    @pytest.mark.parametrize(
        "expected_result, unsearchable", [(True, True), (False, False)]
    )
    def test_is_valid_unsearchable_key_generic_field(
        self, pack: Pack, expected_result, unsearchable
    ):
        """
        Given
            - A generic field which unsearchable is true
            - A generic field which unsearchable is false
        When
            - Run the validate command.
        Then
            - validate that is_valid_unsearchable_key expected answer
        """
        generic_field = pack.create_generic_field("MyGenericField")
        generic_field.update({"unsearchable": unsearchable})
        structure = StructureValidator(generic_field.path)
        res_validator = GenericFieldValidator(structure)
        assert res_validator.is_valid_unsearchable_key() is expected_result

    @pytest.mark.parametrize(
        "expected_result, unsearchable, is_added_file",
        [
            (True, True, True),
            (False, False, True),
            (True, True, False),
            (True, False, False),
        ],
    )
    def test_is_valid_file_generic_field(
        self, mocker, pack: Pack, expected_result, unsearchable, is_added_file
    ):
        """
        Given
            - A generic field which unsearchable is true, is_added_file is false
            - A generic field which unsearchable is false, is_added_file is false
            - A generic field which unsearchable is true, is_added_file is true
            - A generic field which unsearchable is false, is_added_file is true
        When
            - Run the validate command.
        Then
            - validate that is_valid_file is expected answer
        """
        incident_field = pack.create_generic_field("MyField")
        incident_field.update({"unsearchable": unsearchable})
        structure = StructureValidator(incident_field.path)
        res_validator = GenericFieldValidator(structure)
        mocker.patch.object(
            ContentEntityValidator, "is_valid_generic_object_file", return_value=True
        )
        mocker.patch.object(GenericFieldValidator, "is_valid_group", return_value=True)
        mocker.patch.object(
            GenericFieldValidator, "is_valid_id_prefix", return_value=True
        )
        assert (
            res_validator.is_valid_file(validate_rn=False, is_added_file=is_added_file)
            is expected_result
        )

    @pytest.mark.parametrize(
        "expected_result, unsearchable, is_added_file",
        [
            (True, True, True),
            (False, False, True),
            (True, True, False),
            (True, False, False),
        ],
    )
    def test_is_valid_file_incident_field(
        self, mocker, pack: Pack, expected_result, unsearchable, is_added_file
    ):
        """
        Given
            - An incident field which unsearchable is true, is_added_file is false
            - An incident field which unsearchable is false, is_added_file is false
            - An incident field which unsearchable is true, is_added_file is true
            - An incident field which unsearchable is false, is_added_file is true
        When
            - Run the validate command.
        Then
            - validate that is_valid_file is expected answer
        """
        incident_field = pack.create_incident_field("MyField")
        incident_field.update({"unsearchable": unsearchable})
        structure = StructureValidator(incident_field.path)
        res_validator = IncidentFieldValidator(structure)
        mocker.patch.object(ContentEntityValidator, "is_valid_file", return_value=True)
        mocker.patch.object(IncidentFieldValidator, "is_valid_type", return_value=True)
        mocker.patch.object(IncidentFieldValidator, "is_valid_group", return_value=True)
        mocker.patch.object(
            IncidentFieldValidator, "is_valid_content_flag", return_value=True
        )
        mocker.patch.object(
            IncidentFieldValidator, "is_valid_system_flag", return_value=True
        )
        mocker.patch.object(
            IncidentFieldValidator, "is_valid_cli_name", return_value=True
        )
        mocker.patch.object(
            IncidentFieldValidator, "is_valid_version", return_value=True
        )
        mocker.patch.object(
            IncidentFieldValidator, "is_valid_required", return_value=True
        )
        assert (
            res_validator.is_valid_file(validate_rn=False, is_added_file=is_added_file)
            is expected_result
        )


def test_skip_conf_json(mocker):
    """ "
    Given
        `skip_conf_json` argument for validate set to `True` or `False`
    When
        - Running validate with `skip_conf_json`
    Then
        -
          - If set to `True`, the `ConfJsonValidator` shouldn't be called.
          - If set to `False`, the `ConfJsonValidator` should be called.

    """
    from demisto_sdk.commands.common.hook_validations.conf_json import ConfJsonValidator

    conf_json_init = mocker.patch.object(ConfJsonValidator, "load_conf_file")
    OldValidateManager(skip_conf_json=False)
    conf_json_init.asssert_called()
    conf_json_init = mocker.patch.object(ConfJsonValidator, "load_conf_file")
    OldValidateManager(skip_conf_json=True)
    conf_json_init.asssert_not_called()


@pytest.mark.parametrize(
    "pack_name, expected", [("NonSupported", False), ("PackName1", True)]
)
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
    validate_manager = OldValidateManager(check_is_unskipped=False, skip_conf_json=True)
    res = validate_manager.should_raise_pack_version(pack_name)
    assert res == expected


pack_metadata = {
    "name": "ForTesting",
    "description": "A descriptive description.",
    "support": "xsoar",
    "currentVersion": "1.0.0",
    "author": "Cortex XSOAR",
    "url": "https://www.paloaltonetworks.com/cortex",
    "email": "",
    "categories": ["Data Enrichment & Threat Intelligence"],
    "tags": [],
    "useCases": [],
    "keywords": [],
}


@pytest.mark.parametrize("pack_metadata", [(pack_metadata)])
def test_run_validation_using_git_on_only_metadata_changed(
    mocker, pack: Pack, pack_metadata
):
    """
    Given
        - metadata file that was changed.
    When
        - Run all tests on the file.
    Then
        - validate That no error returns.
    """
    pack.pack_metadata.write_json(pack_metadata)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value=True)
    mocker.patch.object(
        OldValidateManager,
        "get_changed_files_from_git",
        return_value=(set(), set(), {pack.pack_metadata.path}, set(), True),
    )
    mocker.patch.object(
        tools, "get_dict_from_file", return_value=({"approved_list": []}, "json")
    )
    mocker.patch.object(GitUtil, "deleted_files", return_value=set())
    mocker.patch(
        "demisto_sdk.commands.common.hook_validations.integration.tools.get_current_categories",
        return_value=["Data Enrichment & Threat Intelligence"],
    )
    validate_manager = OldValidateManager(check_is_unskipped=False, skip_conf_json=True)
    with ChangeCWD(pack.repo_path):
        res = validate_manager.run_validation_using_git()
    assert res


def test_validate_using_git_on_changed_marketplaces(mocker, pack, caplog):
    """
    Given:
        -   Modified marketplaces in pack_metadata
        -   Other content items in the pack (specifically an integration)

    When:
        -   Running validate -g

    Then:
        -   Ensure the pack's content items are validated.
    """

    old_pack_metadata = pack_metadata.copy()
    old_pack_metadata["marketplaces"] = ["xsoar"]
    new_pack_metadata = pack_metadata.copy()
    new_pack_metadata["marketplaces"] = ["xsoar", "marketplacev2"]

    pack.pack_metadata.write_json(new_pack_metadata)
    some_integration = pack.create_integration("SomeIntegration")
    some_integration.create_default_integration()
    # Integration with invalid version
    some_integration.yml.update(
        {"commonfields": {"id": "some_integration", "version": 2}}
    )
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value=True)

    # Integration was not modified, pack_metadata was
    mocker.patch.object(
        OldValidateManager,
        "get_changed_files_from_git",
        return_value=(
            set(),
            set(),
            {tools.get_relative_path_from_packs_dir(pack.pack_metadata.path)},
            set(),
            True,
        ),
    )
    mocker.patch.object(GitUtil, "deleted_files", return_value=set())
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_remote_file",
        return_value=old_pack_metadata,
    )
    validate_manager = OldValidateManager(check_is_unskipped=False, skip_conf_json=True)

    with ChangeCWD(pack.repo_path):
        result = validate_manager.run_validation_using_git()

    assert not result
    assert len(validate_manager.packs_with_mp_change) == 1

    expected_string, expected_code = Errors.wrong_version()
    assert expected_string in caplog.text
    assert expected_code in caplog.text


def test_is_mapping_fields_command_exist(integration):
    """
    Given
    - Integration yml file with get-mapping-fields command.

    When
    - Checking if get-mapping-fields command exists.

    Then
    -  validator returns the True.
    """
    integration.yml.write_dict(
        {"script": {"commands": [{"name": "get-mapping-fields"}], "ismappable": True}}
    )
    structure_validator = StructureValidator(
        integration.yml.path, predefined_scheme="integration"
    )
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
    integration.yml.write_dict(
        {
            "script": {
                "commands": [{"name": "not-get-mapping-fields"}],
                "ismappable": True,
            }
        }
    )

    with ChangeCWD(integration.repo_path):
        structure_validator = StructureValidator(
            integration.yml.path, predefined_scheme="integration"
        )
        validator = IntegrationValidator(structure_validator)

        assert not validator.is_mapping_fields_command_exist()


def test_get_packs_that_should_have_version_raised(mocker, repo):
    """
    Given
    - Different files from different packs in several statuses:
      1. Modified integration
      2. Modified test-playbook
      3. Added script to new pack
      4. Added script to existing pack
      5. Modified old format script
      6. Modified dependencies field in pack_metadata.json file
      7. Modified tags field in pack_metadata.json file

    When
    - Running get_packs_that_should_have_version_raised.

    Then
    -  The returning set includes the packs for 1, 4, 5 & 6 and does not include the packs for 2, 3 & 7.
    """
    existing_pack1 = repo.create_pack("PackWithModifiedIntegration")
    moodified_integration = existing_pack1.create_integration("MyIn")
    moodified_integration.create_default_integration()

    existing_pack2 = repo.create_pack("ExistingPackWithAddedScript")
    added_script_existing_pack = existing_pack2.create_script("MyScript")
    added_script_existing_pack.create_default_script()

    new_pack = repo.create_pack("NewPack")
    added_script_new_pack = new_pack.create_script("MyNewScript")
    added_script_new_pack.create_default_script()

    existing_pack3 = repo.create_pack("PackWithModifiedOldFile")
    modified_old_format_script = existing_pack3.create_script("OldScript")
    modified_old_format_script.create_default_script()

    existing_pack4 = repo.create_pack("PackWithModifiedTestPlaybook")
    moodified_test_playbook = existing_pack4.create_test_playbook("TestBook")
    moodified_test_playbook.create_default_test_playbook()

    existing_pack6 = repo.create_pack("PackWithModifiedMetadataDependencies")
    new_pack_metadata6 = pack_metadata.copy()
    new_pack_metadata6["dependencies"] = {"Base": {"mandatory": True, "name": "Base"}}
    existing_pack6.pack_metadata.write_json(new_pack_metadata6)

    existing_pack7 = repo.create_pack("PackWithModifiedMetadataTags")
    new_pack_metadata7 = pack_metadata.copy()
    new_pack_metadata7["tags"] = ["tag"]
    existing_pack7.pack_metadata.write_json(new_pack_metadata7)

    validate_manager = OldValidateManager(check_is_unskipped=False)
    validate_manager.new_packs = {"NewPack"}

    modified_files = {
        moodified_integration.yml.rel_path,
        moodified_test_playbook.yml.rel_path,
    }
    added_files = {
        added_script_existing_pack.yml.rel_path,
        added_script_new_pack.yml.rel_path,
    }
    old_files = {modified_old_format_script.yml.rel_path}

    changed_meta_files = {
        tools.get_relative_path_from_packs_dir(existing_pack6.pack_metadata.path),
        tools.get_relative_path_from_packs_dir(existing_pack7.pack_metadata.path),
    }
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_remote_file",
        return_value=pack_metadata,
    )
    with ChangeCWD(repo.path):
        packs_that_should_have_version_raised = (
            validate_manager.get_packs_that_should_have_version_raised(
                modified_files=modified_files,
                added_files=added_files,
                old_format_files=old_files,
                changed_meta_files=changed_meta_files,
            )
        )

        assert "PackWithModifiedIntegration" in packs_that_should_have_version_raised
        assert "ExistingPackWithAddedScript" in packs_that_should_have_version_raised
        assert "PackWithModifiedOldFile" in packs_that_should_have_version_raised
        assert (
            "PackWithModifiedTestPlaybook" not in packs_that_should_have_version_raised
        )
        assert "NewPack" not in packs_that_should_have_version_raised
        assert (
            "PackWithModifiedMetadataDependencies"
            in packs_that_should_have_version_raised
        )
        assert (
            "PackWithModifiedMetadataTags" not in packs_that_should_have_version_raised
        )


def test_quiet_bc_flag(repo):
    existing_pack1 = repo.create_pack("PackWithModifiedIntegration")
    moodified_integration = existing_pack1.create_integration("MyIn")
    moodified_integration.create_default_integration()


def test_check_file_relevance_and_format_path_non_formatted_relevant_file(mocker):
    """
    Given
    - file path to validate

    When
    - file is relevant for validation and should not be formatted

    Then
    - return the file path
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=FileType.INTEGRATION,
    )
    mocker.patch.object(validator_obj, "is_old_file_format", return_value=False)
    input_file_path = "Packs/PackName/Integrations/IntegrationName/IntegrationName.yml"
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, None, set()
    ) == (input_file_path, "", True)


@pytest.mark.parametrize(
    "input_file_path",
    [
        "Packs/pack_id/Integrations/integration_id/test_data/file.json",
        "Packs/pack_id/test_data/file.json",
        "Packs/pack_id/Scripts/script_id/test_data/file.json",
        "Packs/pack_id/TestPlaybooks/test_data/file.json",
        "Packs/pack_id/Integrations/integration_id/command_examples.txt",
        "Packs/pack_id/Integrations/integration_id/.vulture_whitelist.py",
    ],
)
def test_check_file_relevance_and_format_path_ignored_files(input_file_path):
    """
    Given
    - file path to validate

    When
    - file path is of a file that should be ignored

    Then
    - return None, file is ignored
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, None, set()
    ) == ("", "", True)


@pytest.mark.parametrize(
    "input_file_path",
    [
        "OtherDir/Integration/file.json",
        "TestData/file.json",
        "TestPlaybooks/file.yml",
        "docs/dbot/README.md",
    ],
)
def test_check_file_relevance_and_format_path_ignored_non_pack_files(input_file_path):
    """
    Given
    - file path to validate

    When
    - file is not in Packs directory

    Then
    - return None, file is ignored
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, None, set()
    ) == ("", "", True)


@pytest.mark.parametrize(
    "input_file_path",
    [".gitlab/ci/check.yml", ".github/ci/check.yml", ".circleci/ci/check.yml"],
)
def test_check_file_relevance_and_format_path_ignored_git_and_circle_files(
    input_file_path,
):
    """
    Given
    - file path to validate

    When
    - file path is a gitlab/circleci/github file

    Then
    - return None, file is ignored
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, None, set()
    ) == ("", "", True)


def test_check_file_relevance_and_format_path_type_missing_file(mocker, caplog):
    """
    Given
    - file path to validate

    When
    - file type is not supported

    Then
    - make sure that empty strings are returned
    - make sure BA102 is returned as the file cannot be recognized
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)

    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=None,
    )
    assert validator_obj.check_file_relevance_and_format_path(
        "Packs/type_missing_filename", None, set()
    ) == ("", "", False)

    assert (
        "[BA102] - File Packs/type_missing_filename is not supported in the validate command"
    ) in caplog.text


@pytest.mark.parametrize(
    "input_file_path, file_type",
    [
        ("Packs/some_test.py", FileType.PYTHON_FILE),
        ("Packs/some_file.Tests.ps1", FileType.POWERSHELL_FILE),
        ("Packs/some_test.js", FileType.JAVASCRIPT_FILE),
    ],
)
def test_check_file_relevance_and_format_path_ignore_test_file(
    mocker, input_file_path, file_type
):
    """
    Given
    - file path to validate

    When
    - file is a test file

    Then
    - return None, file is ignored
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=file_type,
    )
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, None, set()
    ) == ("", "", True)


@pytest.mark.parametrize(
    "input_file_path, file_type",
    [
        ("Packs/some_file.py", FileType.PYTHON_FILE),
        ("Packs/some_file.ps1", FileType.POWERSHELL_FILE),
        ("Packs/some_file.js", FileType.JAVASCRIPT_FILE),
        ("Packs/some_file.xif", FileType.XIF_FILE),
    ],
)
def test_check_file_relevance_and_format_path_file_to_format(
    mocker, input_file_path, file_type
):
    """
    Given
    - file path to validate

    When
    - file should be formatted

    Then
    - return the formatted file path
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=file_type,
    )
    mocker.patch.object(validator_obj, "is_old_file_format", return_value=False)
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, None, set()
    ) == ("Packs/some_file.yml", "", True)


@pytest.mark.parametrize(
    "input_file_path, file_type",
    [
        ("Packs/PackName/ParsingRules/Name/some_file.xif", FileType.MODELING_RULE_XIF),
    ],
)
def test_check_file_relevance_and_format_path_file_to_format_parsing_rules(
    mocker, input_file_path, file_type
):
    """
    Given
    - parsing rule (xif) file path to validate

    When
    - file should be formatted when checking file relevancy for new release notes

    Then
    - return the formatted file path
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=file_type,
    )
    mocker.patch.object(validator_obj, "is_old_file_format", return_value=False)
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, None, set()
    ) == ("Packs/PackName/ParsingRules/Name/some_file.yml", "", True)


@pytest.mark.parametrize(
    "input_file_path, old_file_path, file_type",
    [
        ("Packs/some_file.py", "Packs/old_file_path.py", FileType.PYTHON_FILE),
        ("Packs/some_file.ps1", "Packs/old_file_path.ps1", FileType.POWERSHELL_FILE),
        ("Packs/some_file.js", "Packs/old_file_path.js", FileType.JAVASCRIPT_FILE),
    ],
)
def test_check_file_relevance_and_format_path_file_to_format_with_old_path(
    mocker, input_file_path, old_file_path, file_type
):
    """
    Given
    - file path to validate and it's old path

    When
    - file should be formatted and it has been renamed

    Then
    - return tuple of the formatted path and it's original path
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=file_type,
    )
    mocker.patch.object(validator_obj, "is_old_file_format", return_value=False)
    assert validator_obj.check_file_relevance_and_format_path(
        input_file_path, old_file_path, set()
    ) == ("Packs/some_file.yml", "Packs/old_file_path.yml", True)


def test_check_file_relevance_and_format_path_old_format_file(mocker):
    """
    Given
    - file path to validate

    When
    - file is of an old format

    Then
    - return None, add the file path to the old_format_files argument
    """
    validator_obj = OldValidateManager(is_external_repo=True, check_is_unskipped=False)
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=FileType.INTEGRATION,
    )
    mocker.patch.object(validator_obj, "is_old_file_format", return_value=True)
    old_format_files: set = set()
    assert validator_obj.check_file_relevance_and_format_path(
        "Packs/some_test.yml", None, old_format_files
    ) == ("", "", True)
    assert old_format_files == {"Packs/some_test.yml"}


@pytest.mark.parametrize("is_feed", (True, False))
def test_job_sanity(repo, is_feed: bool):
    """
    Given
            A Job object in a repo
    When
            Validating the file
    Then
            Ensure the autogenerated Job files pass
    """
    pack = repo.create_pack()
    job = pack.create_job(is_feed=is_feed, name="job_name")
    validate_manager = OldValidateManager(
        check_is_unskipped=False, file_path=job.path, skip_conf_json=True
    )

    with ChangeCWD(repo.path):
        assert validate_manager.validate_job(
            StructureValidator(job.path, is_new_file=True),
            pack_error_ignore_list=list(),
        )


@pytest.mark.parametrize("is_feed", (True, False))
@pytest.mark.parametrize("version", ("6.4.9", ""))
def test_job_from_version(repo, mocker, caplog, is_feed: bool, version: Optional[str]):
    """
    Given
            A valid Job object in a repo
    When
            Validating the file
    Then
            Ensure the autogenerated Job files pass
    """

    pack = repo.create_pack()
    job = pack.create_job(is_feed, "job_name")
    job.update({"fromVersion": version})
    validate_manager = OldValidateManager(
        check_is_unskipped=False, file_path=job.path, skip_conf_json=True
    )

    with ChangeCWD(repo.path):
        assert not validate_manager.validate_job(
            StructureValidator(job.path, is_new_file=True),
            pack_error_ignore_list=list(),
        )
    assert (
        f"fromVersion field in Job needs to be at least {FILETYPE_TO_DEFAULT_FROMVERSION.get(FileType.JOB)} (found {version})"
    ) in caplog.text


def test_job_non_feed_with_selected_feeds(repo, caplog):
    """
    Given
            A Job object in a repo, with non-empty selectedFeeds when isFeed is set to false
    When
            Validating the file
    Then
            Ensure an error is raised, and validation fails
    """

    pack = repo.create_pack()
    job = pack.create_job(is_feed=False, name="job_name", selected_feeds=["feed_name"])
    validate_manager = OldValidateManager(
        check_is_unskipped=False, file_path=job.path, skip_conf_json=True
    )

    with ChangeCWD(repo.path):
        assert not validate_manager.validate_job(
            StructureValidator(job.path, is_new_file=True),
            pack_error_ignore_list=list(),
        )
    assert (
        "Job objects cannot have non-empty selectedFeeds when isFeed is set to false"
    ) in caplog.text


def test_job_both_selected_and_all_feeds_in_job(repo, caplog):
    """
    Given
            A Job object in a repo, with non-empty selectedFeeds values but isAllFields set to true
    When
            Validating the file
    Then
            Ensure an error is raised, and validation fails
    """

    pack = repo.create_pack()
    job = pack.create_job(is_feed=True, name="job_name", selected_feeds=["feed_name"])
    job.update({"isAllFeeds": True})
    validate_manager = OldValidateManager(
        check_is_unskipped=False, file_path=job.path, skip_conf_json=True
    )

    with ChangeCWD(repo.path):
        assert not validate_manager.validate_job(
            StructureValidator(job.path, is_new_file=True),
            pack_error_ignore_list=list(),
        )
    assert (
        "Job cannot have non-empty selectedFeeds values when isAllFields is set to true"
    ) in caplog.text


@pytest.mark.parametrize("is_feed", (True, False))
@pytest.mark.parametrize("name", ("", " ", "  ", "\n", "\t"))
def test_job_blank_name(repo, mocker, name: str, is_feed: bool, caplog):
    """
    Given
            A Job object in a repo, with a blank (space/empty) value as its name
    When
            Validating the file
    Then
            Ensure an error is raised, and validation fails
    """

    pack = repo.create_pack()
    job = pack.create_job(is_feed=is_feed, name=name)
    job.update(
        {"name": name}
    )  # name is appended with number in create_job, so it must be explicitly set here

    validate_manager = OldValidateManager(
        check_is_unskipped=False, file_path=job.path, skip_conf_json=True
    )

    with ChangeCWD(repo.path):
        assert not validate_manager.validate_job(
            StructureValidator(job.path, is_new_file=True),
            pack_error_ignore_list=list(),
        )
    expected_string, expected_code = Errors.empty_or_missing_job_name()
    assert all([expected_string in caplog.text, expected_code in caplog.text])


@pytest.mark.parametrize("is_feed", (True, False))
def test_job_missing_name(repo, caplog, is_feed: bool):
    """
    Given
            A Job object in a repo, with an empty value as name
    When
            Validating the file
    Then
            Ensure an error is raised, and validation fails
    """

    pack = repo.create_pack()
    job = pack.create_job(is_feed=is_feed)
    job.remove(
        "name"
    )  # some name is appended with number in create_job, so it must be explicitly removed

    validate_manager = OldValidateManager(
        check_is_unskipped=False, file_path=job.path, skip_conf_json=True
    )

    with ChangeCWD(repo.path):
        assert not validate_manager.validate_job(
            StructureValidator(job.path, is_new_file=True),
            pack_error_ignore_list=list(),
        )
    expected_string, expected_code = Errors.empty_or_missing_job_name()
    assert all([expected_string in caplog.text, expected_code in caplog.text])


@pytest.mark.parametrize(
    "is_all_feeds,selected_feeds",
    ((True, []), (True, None), (False, ["my_field"]), (True, ["my_field"])),
)
def test_job_unexpected_field_values_in_non_feed_job(
    repo, caplog, monkeypatch, is_all_feeds: bool, selected_feeds: Optional[List[str]]
):
    """
    Given
            A Job object in a repo, with non-empty selectedFeeds when isFeed is set to false
    When
            Validating the file
    Then
            Ensure an error is raised, and validation fails
    """

    pack = repo.create_pack()
    job = pack.create_job(is_feed=True, name="job_name")
    job.update({"isAllFeeds": False})
    validate_manager = OldValidateManager(
        check_is_unskipped=False, file_path=job.path, skip_conf_json=True
    )

    with ChangeCWD(repo.path):
        assert not validate_manager.validate_job(
            StructureValidator(job.path, is_new_file=True),
            pack_error_ignore_list=list(),
        )
    assert (
        "Job must either have non-empty selectedFeeds OR have isAllFields set to true when isFeed is set to true"
    ) in caplog.text


@pytest.mark.parametrize(
    "file_set,expected_info_output,expected_error_output,expected_result,added_files",
    (
        ({"Packs/Integration/mock_file_description.md"}, "", "[BA115]", False, set()),
        (set(), "", "", True, set()),
        ({"Packs/Integration/doc_files/image.png"}, "", "", True, set()),
        (
            {"Packs/Integration/Playbooks/mock_playbook.yml"},
            "",
            "",
            True,
            {"renamed_mock_playbook.yml"},
        ),
        (
            {Path("Packs/Integration/Playbooks/mock_playbook.yml")},
            "",
            "",
            True,
            {Path("renamed_mock_playbook.yml")},
        ),
        (({"non_content_item.txt"}, "", "[BA115]", False, set())),
    ),
)
def test_validate_deleted_files(
    mocker,
    monkeypatch,
    file_set,
    expected_info_output,
    expected_error_output,
    expected_result,
    added_files,
    caplog,
):
    """
    Given
            A file_path set to validate.
    When
            Validating the files.
    Then
            Assert the expected result (True or False) and the expected output (if there is an expected output).
    """

    validate_manager = OldValidateManager(check_is_unskipped=False, skip_conf_json=True)
    if added_files:
        mocker.patch(
            "demisto_sdk.commands.validate.old_validate_manager._get_file_id",
            return_value="playbook",
        )
        mocker.patch(
            "demisto_sdk.commands.validate.old_validate_manager.get_remote_file",
            return_value={"id": "id"},
        )

    result = validate_manager.validate_deleted_files(file_set, added_files)

    assert expected_result is result
    if expected_info_output:
        assert expected_info_output in caplog.text
    if expected_error_output:
        assert expected_error_output in caplog.text


def test_was_file_renamed_but_labeled_as_deleted(mocker):
    """
    Given
            - `deleted_file_path` - A unified script "ShowCampaignUniqueRecipients" file path
            - The yml path of the splitted script in `added_files`.
    When
            Validating deleted files.
    Then
            Make sure the file is considered as renamed.
    """
    deleted_file_path = "Packs/Campaign/Scripts/script-ShowCampaignUniqueRecipients.yml"
    added_files = [
        "Packs/Campaign/Scripts/ShowCampaignUniqueRecipients/ShowCampaignUniqueRecipients.yml"
    ]
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_remote_file",
        return_value={"commonfields": {"id": "ShowCampaignUniqueRecipients"}},
    )
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_file",
        return_value={"commonfields": {"id": "ShowCampaignUniqueRecipients"}},
    )

    result = OldValidateManager.was_file_renamed_but_labeled_as_deleted(
        deleted_file_path,
        added_files,
    )
    assert result


def test_validate_contributors_file(repo):
    """
    Given:
        A simple CONTRIBUTORS.js file (see this https://xsoar.pan.dev/docs/packs/packs-format#contributors)
    When:
        Running validation on the new file
    Then:
        Ensure the file is passing validation
    """

    pack = repo.create_pack()
    with ChangeCWD(repo.path):
        contributors_file = pack.create_contributors_file('["- Test UserName"]')

        validate_manager = OldValidateManager(
            check_is_unskipped=False,
            file_path=contributors_file.path,
            skip_conf_json=True,
        )
        assert validate_manager.run_validation_on_specific_files()


def test_validate_pack_name(repo):
    """
    Given:
        A file in a pack to validate.
    When:
        Checking if the pack name of the file is valid (the pack name is not changed).
    Then:
        If new file or unchanged pack then `true`, else `false`.

    """
    validator_obj = OldValidateManager()
    assert validator_obj.is_valid_pack_name("Packs/original_pack/file", None, None)
    assert validator_obj.is_valid_pack_name(
        "Packs/original_pack/file", "Packs/original_pack/file", None
    )
    assert not validator_obj.is_valid_pack_name(
        "Packs/original_pack/file", "Packs/original_pack_v2/file", None
    )


def test_image_error(set_git_test_env, caplog):
    """
    Given
            a image that isn't located in the right folder.
    When
            Validating the file
    Then
            Ensure an error is raised, and  the right error is given.
    """

    validate_manager = OldValidateManager()
    validate_manager.run_validations_on_file(IGNORED_PNG, None)
    expected_string, expected_code = Errors.invalid_image_name_or_location()
    assert all([expected_string in caplog.text, expected_code in caplog.text])


modeling_rule_file_changes = [
    (
        MODELING_RULES_SCHEMA_FILE,
        FileType.MODELING_RULE_SCHEMA,
        MODELING_RULES_YML_FILE,
    ),
    (MODELING_RULES_XIF_FILE, FileType.MODELING_RULE_XIF, MODELING_RULES_YML_FILE),
    (
        MODELING_RULES_TESTDATA_FILE,
        FileType.MODELING_RULE_TEST_DATA,
        MODELING_RULES_YML_FILE,
    ),
]


@pytest.mark.parametrize("f_path, f_type, expected_result", modeling_rule_file_changes)
def test_check_file_relevance_and_format_path(mocker, f_path, f_type, expected_result):
    """

    Given: A modeling rules entity file that was changed.

    When: Validating changed files.

    Then: Update the file path to point the modeling rules yml file.

    """
    mocker.patch.object(
        OldValidateManager, "ignore_files_irrelevant_for_validation", return_value=False
    )
    mocker.patch.object(OldValidateManager, "is_old_file_format", return_value=False)
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.find_type",
        return_value=f_type,
    )
    validate_manager = OldValidateManager()
    file_path, old_path, _ = validate_manager.check_file_relevance_and_format_path(
        f_path, f_path, set()
    )
    assert file_path == old_path == expected_result


pack_metadata_invalid_tags = {
    "name": "ForTesting",
    "description": "A descriptive description.",
    "support": "xsoar",
    "currentVersion": "1.0.0",
    "author": "Cortex XSOAR",
    "url": "https://www.paloaltonetworks.com/cortex",
    "email": "",
    "categories": ["Data Enrichment & Threat Intelligence"],
    "tags": ["Use Case"],
    "useCases": [],
    "keywords": [],
    "marketplaces": ["xsoar"],
}


@pytest.mark.parametrize("pack_metadata_info", [pack_metadata_invalid_tags])
def test_run_validation_using_git_on_metadata_with_invalid_tags(
    mocker, monkeypatch, repo, pack_metadata_info, caplog
):
    """
    Given
        - A Pack with a Use Case tags but no PB, incidents Types or Layouts. Considered invalid.
        - A git run.
    When
        - Running validations on pack using git.
    Then
        - Assert validation fails and the right error number is shown.
    """

    pack = repo.create_pack()
    pack.pack_metadata.write_json(pack_metadata_info)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value=True)
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(
            {tools.get_relative_path_from_packs_dir(pack.pack_metadata.path)},
            set(),
            set(),
        ),
    )
    mocker.patch.object(GitUtil, "deleted_files", return_value=set())
    validate_manager = OldValidateManager(check_is_unskipped=False, skip_conf_json=True)
    std_output = StringIO()
    with contextlib.redirect_stdout(std_output):
        with ChangeCWD(repo.path):
            res = validate_manager.run_validation_using_git()
    assert "[PA123]" in caplog.text
    assert not res


@pytest.mark.parametrize(
    "modified_files, added_files, changed_meta_files, old_format_files, deleted_files",
    [
        (
            {"modified_files"},
            {"added_files"},
            {"changed_meta_files"},
            {"old_format_files"},
            {"deleted_files"},
        ),
        (set(), {"added_files"}, set(), set(), set()),
        (set(), set(), {"changed_meta_files"}, set(), set()),
        (set(), set(), set(), {"old_format_files"}, set()),
        (set(), set(), set(), set(), {"deleted_files"}),
    ],
)
def test_run_validation_using_git_validation_calls(
    mocker,
    modified_files: set,
    added_files: set,
    changed_meta_files: set,
    old_format_files: set,
    deleted_files: set,
):
    """
    Given: Some changed files were detected.

    When: Running validations on using git.

    Then: Ensure the correct validations are called on the correct files.
    """
    validate_manager = OldValidateManager()

    mocker.patch.object(validate_manager, "setup_git_params", return_value=True)
    mocker.patch.object(
        validate_manager,
        "get_changed_meta_files_that_should_have_version_raised",
        return_value=set(),
    )
    mocker.patch.object(
        validate_manager,
        "get_changed_files_from_git",
        return_value=(
            modified_files,
            added_files,
            changed_meta_files,
            old_format_files,
            True,
        ),
    )
    mocker.patch.object(GitUtil, "deleted_files", return_value=deleted_files)

    modified_files_validation = mocker.patch.object(
        validate_manager, "validate_modified_files", return_value=True
    )
    added_files_validation = mocker.patch.object(
        validate_manager, "validate_added_files", return_value=True
    )
    no_old_format_validation = mocker.patch.object(
        validate_manager, "validate_no_old_format", return_value=True
    )
    deleted_files_validation = mocker.patch.object(
        validate_manager, "validate_deleted_files", return_value=True
    )

    validate_manager.run_validation_using_git()

    modified_files_validation.assert_called_once_with(modified_files | old_format_files)
    added_files_validation.assert_called_once_with(added_files, modified_files)

    if old_format_files:
        no_old_format_validation.assert_called_once_with(old_format_files)

    else:
        assert not no_old_format_validation.called

    deleted_files_validation.assert_called_once_with(deleted_files, added_files)


def test_validate_no_disallowed_terms_in_customer_facing_docs_success():
    """
    Given:
    - Content of a customer-facing docs file (README, Release Notes, etc.)

    When:
    - Validating the content doesn't contain disallowed terms

    Then:
    - Ensure that if no disallowed terms are found, True is returned
    """
    file_content = "This is an example with no disallowed terms within it."

    base_validator = BaseValidator()
    assert base_validator.validate_no_disallowed_terms_in_customer_facing_docs(
        file_content=file_content, file_path=""
    )


@pytest.mark.parametrize(
    "file_content",
    [
        "This is an example with the 'test-module' term within it.",
        "This is an example with the 'Test-Module' term within it",  # Assure case-insensitivity
    ],
)
def test_validate_no_disallowed_terms_in_customer_facing_docs_failure(
    file_content: str,
):
    """
    Given:
    - Content of a customer-facing docs file (README, Release Notes, etc.)

    When:
    - Validating the content doesn't contain disallowed terms

    Then:
    - Ensure that if a disallowed term is found, False is returned
    """
    base_validator = BaseValidator()
    assert not base_validator.validate_no_disallowed_terms_in_customer_facing_docs(
        file_content=file_content, file_path=""
    )


def test_validate_no_disallowed_terms_in_customer_facing_docs_end_to_end(repo, caplog):
    """
    Given:
    - Content of a customer-facing docs file (README, Release Notes, etc.)

    When:
    - Validating the content doesn't contain disallowed terms

    Then:
    - Ensure that if a disallowed term is found, False is returned, and True otherwise.
    """

    file_content = "This is an example with the 'test-module' term within it."

    pack = repo.create_pack()
    rn_file = pack.create_release_notes(version="1_0_0", content=file_content)
    integration = pack.create_integration(readme=file_content, description=file_content)
    integration_readme_file = integration.readme
    integration_description_file = integration.description
    playbook_readme_file = pack.create_playbook(readme=file_content).readme
    with ChangeCWD(pack.repo_path):
        validate_manager = OldValidateManager()

        assert not validate_manager.run_validations_on_file(
            file_path=rn_file.path, pack_error_ignore_list=[]
        )
        assert not validate_manager.run_validations_on_file(
            file_path=integration_readme_file.path, pack_error_ignore_list=[]
        )
        assert not validate_manager.run_validations_on_file(
            file_path=integration_description_file.path, pack_error_ignore_list=[]
        )
        assert not validate_manager.run_validations_on_file(
            file_path=playbook_readme_file.path, pack_error_ignore_list=[]
        )

        # Assure errors were logged (1 error per validated file)
        assert caplog.text.count("BA125") == 4


@pytest.mark.parametrize(
    "modified_files, new_file_content, remote_file_content, local_file_content, expected_results",
    [
        (
            {"Packs/test/.pack-ignore"},
            "[file:test.yml]\nignore=BA108,BA109,\n",
            "[file:test.yml]\nignore=BA108,BA109,\n",
            "",
            set(),
        ),
        (
            {"Packs/test1/.pack-ignore"},
            "[file:test.yml]\nignore=BA108,BA109,\n",
            "[file:test2.yml]\nignore=BA108,BA109,\n",
            "",
            {
                "Packs/test1/Integrations/test/test.yml",
                "Packs/test1/Integrations/test2/test2.yml",
            },
        ),
        (
            {"Packs/test/.pack-ignore"},
            "[file:test.yml]\nignore=BA108\n",
            b"",
            "",
            {
                "Packs/test/Integrations/test/test.yml",
            },
        ),
        (
            {"Packs/test1/.pack-ignore"},
            "[file:test.yml]\nignore=BA108,BA109,\n[file:test2.yml]\nignore=BA108,BA109,\n",
            {},
            "[file:test.yml]\nignore=BA108,BA109,\n",
            {"Packs/test1/Integrations/test2/test2.yml"},
        ),
        (
            {"Packs/test/.pack-ignore"},
            "[file:test.yml]\nignore=BA108\n",
            b"\n\n",
            "",
            {
                "Packs/test/Integrations/test/test.yml",
            },
        ),
        (
            {"Packs/test/.pack-ignore"},
            "[file:test.yml]\nignore=BA108\n",
            b"    ",
            "",
            {
                "Packs/test/Integrations/test/test.yml",
            },
        ),
        (
            {"Packs/test/.pack-ignore"},
            "[file:test.yml]\nignore=BA108\n",
            b"    \n   \n   ",
            "",
            {
                "Packs/test/Integrations/test/test.yml",
            },
        ),
    ],
)
def test_get_all_files_edited_in_pack_ignore(
    mocker,
    modified_files,
    new_file_content,
    remote_file_content,
    local_file_content,
    expected_results,
):
    """
    Given:
    - modified files set, edited pack-ignore mock, and master's pack-ignore mock.
    - Case 1: pack-ignore mocks which vary by 1 validation.
    - Case 2: pack-ignore mocks which no differences.
    - Case 3: pack-ignore mocks where each file is pointed to a different integration yml.
    - Case 4: old .pack-ignore that is empty and current .pack-ignore that was updated with ignored validation
    - Case 5: old .pack-ignore which is not in the remote branch repo, but only exist in the local branch
    - Case 6: old empty .pack-ignore which contains newlines.
    - Case 7: old empty .pack-ignore which contains only spaces.
    - Case 8: old empty .pack-ignore which contains only spaces and newlines.

    When:
    - Running get_all_files_edited_in_pack_ignore.

    Then:
    - Ensure that the right files were returned.
    - Case 1: Should return the file path only from the relevant pack (there's a similar file in a different pack)
    - Case 2: Should return empty set of extra files to test.
    - Case 3: Should return both file names.
    - Case 4: Ensure the file that was changed in the .pack-ignore is collected
    - Case 5: Ensure the file that was changed in the .pack-ignore is collected from the local repo
    - Case 6 + 7 + 8: Ensure the file that was changed in the .pack-ignore is collected
    """
    mocker.patch.object(
        GitUtil,
        "get_all_files",
        return_value={
            Path("Packs/test/Integrations/test/test.yml"),
            Path("Packs/test1/Integrations/test/test.yml"),
            Path("Packs/test1/Integrations/test2/test2.yml"),
        },
    )
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_remote_file",
        return_value=remote_file_content,
    )
    mocker.patch.object(GitUtil, "find_primary_branch", return_value="main")
    mocker.patch.object(
        GitUtil, "get_local_remote_file_content", return_value=local_file_content
    )
    validate_manager = OldValidateManager()
    config = ConfigParser(allow_no_value=True)
    config.read_string(new_file_content)

    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_pack_ignore_content",
        return_value=config,
    )
    assert (
        validate_manager.get_all_files_edited_in_pack_ignore(modified_files)
        == expected_results
    )


def test_get_all_files_edited_in_pack_ignore_with_git_error(mocker, caplog):
    """
    Given:
    - empty .pack-ignore returned from git api
    - an exception raised when trying to retrieve the .pack-ignore locally

    When:
    - Running get_all_files_edited_in_pack_ignore.

    Then:
    - Ensure no exception is raised
    - ensure that the updated file from the new .pack-ignore is found
    """
    from git import GitCommandError

    caplog.set_level("WARNING")

    mocker.patch.object(
        GitUtil,
        "get_all_files",
        return_value={
            Path("Packs/test/Integrations/test/test.yml"),
            Path("Packs/test1/Integrations/test/test.yml"),
            Path("Packs/test1/Integrations/test2/test2.yml"),
        },
    )

    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_remote_file",
        return_value={},
    )
    mocker.patch.object(GitUtil, "find_primary_branch", return_value="main")
    mocker.patch.object(
        GitUtil, "get_local_remote_file_content", side_effect=GitCommandError("error")
    )

    validate_manager = OldValidateManager()
    config = ConfigParser(allow_no_value=True)
    config.read_string("[file:test.yml]\nignore=BA108,BA109")

    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_pack_ignore_content",
        return_value=config,
    )

    assert validate_manager.get_all_files_edited_in_pack_ignore(
        {"Packs/test/.pack-ignore"}
    ) == {"Packs/test/Integrations/test/test.yml"}
    assert caplog.text
