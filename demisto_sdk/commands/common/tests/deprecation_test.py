import logging

import pytest

from demisto_sdk.commands.common.hook_validations.deprecation import (
    DeprecationValidator,
)
from demisto_sdk.commands.common.hook_validations.integration import (
    IntegrationValidator,
)
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.tests.integration_test import mock_structure
from TestSuite.test_tools import str_in_call_args_list

mocked_id_set = {
    "scripts": [
        {
            "sdca13-dasde12-ffe13-fdgs352": {
                "name": "script_1",
                "file_path": "script_1.yml",
                "deprecated": True,
                "depends_on": [
                    "ic3_command1",
                    "ic5_command1",
                    "ic6_command3",
                    "script_case_4",
                    "script_case_5",
                    "script_format_case_1" "ifc1_command3",
                    "ifc1_command2",
                ],
            }
        },
        {
            "sdca13-dasde12-ffe13-fdgs353": {
                "name": "script_2",
                "file_path": "script_2.yml",
                "deprecated": False,
                "depends_on": [
                    "ic1_command1",
                    "ic5_command2",
                    "ic6_command1",
                    "ic6_command3",
                    "script_case_3",
                    "script_format_case_1",
                    "ifc1_command3",
                    "ifc1_command2",
                ],
            }
        },
    ],
    "playbooks": [
        {
            "sdca13-dasde12-ffe13-fdgs3541": {
                "name": "playbook_1",
                "file_path": "playbook_1.yml",
                "deprecated": True,
                "implementing_scripts": ["IsIntegrationAvailable"],
                "implementing_playbooks": [
                    "playbook_case_4",
                    "playbook_case_3",
                ],
                "command_to_integration": {
                    "ic3_command1": "integration_case_3",
                    "ic6_command2": "integration_case_6",
                    "ifc1_command1": "integration_format_case_1",
                    "ifc1_command3": "integration_format_case_1",
                },
            }
        },
        {
            "sdca13-dasde12-ffe13-fdgs35as": {
                "name": "playbook_2",
                "file_path": "playbook_2.yml",
                "implementing_scripts": [
                    "script_case_2",
                    "script_case_5",
                    "script_format_case_1",
                ],
                "implementing_playbooks": [
                    "playbook_case_2",
                    "playbook_case_3",
                    "playbook_format_case_1",
                ],
                "command_to_integration": {
                    "ic2_command1": "integration_case_2",
                    "ic5_command2": "integration_case_5",
                    "ic6_command1": "integration_case_6",
                    "ifc1_command1": "integration_format_case_1",
                    "ifc1_command3": "integration_format_case_1",
                    "ic7_command1": "integration_case_777",
                },
            }
        },
    ],
}


def mock_deprecation_manager() -> DeprecationValidator:
    deprecation_validator = DeprecationValidator(mocked_id_set)
    return deprecation_validator


class TestDeprecationValidator:

    INTEGRATIONS_VALIDATIONS_LS = [
        (
            {
                "commonfields": {"id": "integration_case_1"},
                "deprecated": True,
                "script": {"commands": [{"name": "ic1_command1"}]},
            },
            False,
            ["ic1_command1"],
            [],
        ),
        (
            {
                "commonfields": {"id": "integration_case_2"},
                "script": {"commands": [{"name": "ic2_command1", "deprecated": True}]},
            },
            False,
            ["ic2_command1"],
            [],
        ),
        (
            {
                "commonfields": {"id": "integration_case_3"},
                "script": {"commands": [{"name": "ic3_command1", "deprecated": True}]},
            },
            True,
            [],
            ["ic3_command1"],
        ),
        (
            {
                "commonfields": {"id": "integration_case_4"},
                "deprecated": False,
                "script": {"commands": [{"name": "ic4_command1"}]},
            },
            True,
            [],
            ["ic4_command1"],
        ),
        (
            {
                "commonfields": {"id": "integration_case_5"},
                "deprecated": False,
                "script": {
                    "commands": [
                        {"name": "ic5_command1", "deprecated": True},
                        {"name": "ic5_command2"},
                    ]
                },
            },
            True,
            [],
            ["ic5_command1", "ic5_command2"],
        ),
        (
            {
                "commonfields": {"id": "integration_case_6"},
                "script": {
                    "commands": [
                        {"name": "ic6_command1", "deprecated": True},
                        {"name": "ic6_command2", "deprecated": True},
                        {"name": "ic6_command3"},
                    ]
                },
            },
            False,
            ["ic6_command1"],
            ["ic6_command3", "ic6_command2"],
        ),
        (
            {
                "commonfields": {"id": "integration_case_7"},
                "script": {"commands": [{"name": "ic7_command1", "deprecated": True}]},
            },
            True,
            [],
            ["ic7_command1"],
        ),
    ]

    @pytest.mark.parametrize(
        "integration_yml, expected_bool_results, expected_commands_in_errors_ls, expected_commands_not_in_errors_ls",
        INTEGRATIONS_VALIDATIONS_LS,
    )
    def test_validate_integration(
        self,
        mocker,
        monkeypatch,
        integration_yml,
        expected_bool_results,
        expected_commands_in_errors_ls,
        expected_commands_not_in_errors_ls,
    ):
        """
        Given
        - Case 1: integration with one deprecated command that is being used in a none-deprecated script.
        - Case 2: integration with one deprecated command that is being used in a none-deprecated playbook.
        - Case 3: integration with one deprecated command that is being used only in deprecated entities.
        - Case 4: integration with one none-deprecated command that is being used in both deprecated and none-deprecated entities.
        - Case 5: A deprecated integration with two commands, one deprecated and one none-dreprecated:
                  the none-deprecated command is being used in none-deprecated entities only,
                  and the deprecated command is being used in deprecated entities only.
        - Case 6: Integration with two deprecated commands and one none-deprecated command,
                  one deprecated command is being used in deprecated entities only,
                  one deprecated command is being used in none-deprecated entities only,
                  and the none-deprecated is being used in both deprecated and none-deprecated entities.
        - Case 7: Integration with one deprecated command which isn't being used in other entities.
                  However, there's another command with the same name related to a different integration,
                  that is being used in a different integration.
        When
        - Running is_integration_deprecated_and_used on the given integration.
        Then
        - Ensure validation correctly identifies used deprecated commands in none deprecated entities.
        - Case 1: Should return False and that the command name appears in the error massage.
        - Case 2: Should return False and that the command name appears in the error massage.
        - Case 3: Should return True and that no command name appears in the error massage.
        - Case 4: Should return True and that no command name appears in the error massage.
        - Case 5: Should return True and that no command name appears in the error massage.
        - Case 6: Should return False and that only one command name (out of the two deprecated commands) appears in the error massage.
        - Case 7: Should return True and that no command name appears in the error massage.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        structure = mock_structure(current_file=integration_yml)
        validator = IntegrationValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        bool_result = validator.is_integration_deprecated_and_used()
        assert bool_result == expected_bool_results
        for command in expected_commands_in_errors_ls:
            assert str_in_call_args_list(logger_error.call_args_list, command)
        for command in expected_commands_not_in_errors_ls:
            assert not str_in_call_args_list(logger_error.call_args_list, command)

    INTEGRATIONS_FORMAT_VALIDATIONS = [
        (
            {
                "name": "integration_format_case_1",
                "commonfields": {"id": "integration_format_case_1"},
                "script": {
                    "commands": [
                        {"name": "ifc1_command1", "deprecated": True},
                        {"name": "ifc1_command2", "deprecated": True},
                        {"name": "ifc1_command3"},
                    ]
                },
                "tests": ["testplaybook_1", "testplaybook_2"],
            },
            [
                "[IN155] - integration_format_case_1 integration contains deprecated commands that are being used by other entities:\n"
                "ifc1_command1 is being used in the following locations:\nplaybook_2.yml\n"
                "ifc1_command2 is being used in the following locations:\nscript_2.yml\n",
            ],
        )
    ]

    @pytest.mark.parametrize(
        "integration_yml, expected_results", INTEGRATIONS_FORMAT_VALIDATIONS
    )
    def test_validate_integration_error_format(
        self,
        mocker,
        monkeypatch,
        integration_yml,
        expected_results,
    ):
        """
        Given
        - Case 1: Integration with two deprecated commands, one none-deprecated command and two testplaybooks in the tests section,
                  one deprecated command is being used in both deprecated and none-deprecated playbooks,
                  one deprecated command is being used in both deprecated and none-deprecated scripts,
                  and the none-deprecated command is being used in both deprecated and none-deprecated playbooks and scripts.
        When
        - Running is_integration_deprecated_and_used on the given integration.
        Then
        - Ensure the format of the validation is printed out correctly.
        - Case 1: Should print out the given integration and a list of each deprecated command that is being used,
          with a list of files paths of the none-deprecated entities that are using that command under that command.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        structure = mock_structure(current_file=integration_yml)
        validator = IntegrationValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        validator.is_integration_deprecated_and_used()
        for current_expected_results in expected_results:
            assert str_in_call_args_list(
                logger_error.call_args_list, current_expected_results
            )

    SCRIPTS_VALIDATIONS_LS = [
        ({"name": "script_case_1", "deprecated": True}, True),
        ({"name": "script_case_2", "deprecated": True}, False),
        ({"name": "script_case_3", "deprecated": True}, False),
        ({"name": "script_case_4", "deprecated": True}, True),
        ({"name": "script_case_5", "deprecated": False}, True),
    ]

    @pytest.mark.parametrize("script_yml, expected_results", SCRIPTS_VALIDATIONS_LS)
    def test_validate_script(self, script_yml, expected_results):
        """
        Given
        - Case 1: deprecated script that isn't being used in any external entities.
        - Case 2: deprecated script that is being used in none-deprecated entities.
        - Case 3: deprecated script that is being used in a none-deprecated script.
        - Case 4: deprecated script that is being used in a deprecated playbook.
        - Case 5: none-deprecated script that is is being used in both deprecated and none-deprecated entities.

        When
        - Running is_script_deprecated_and_used on the given script.
        Then
        - Ensure validation correctly identifies used deprecated commands in none deprecated entities.
        - Case 1: Should return True.
        - Case 2: Should return False.
        - Case 3: should return False.
        - Case 4: Should return True.
        - Case 5: Should return True.
        """
        structure = mock_structure(current_file=script_yml)
        validator = ScriptValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        assert validator.is_script_deprecated_and_used() == expected_results

    SCRIPTS_FORMAT_VALIDATIONS = [
        (
            {"name": "script_format_case_1", "deprecated": True},
            "[SC107] - script_format_case_1 script is deprecated and being used by the following entities:\nscript_2.yml\nplaybook_2.yml\n",
        )
    ]

    @pytest.mark.parametrize("script_yml, expected_results", SCRIPTS_FORMAT_VALIDATIONS)
    def test_validate_script_error_format(
        self, mocker, monkeypatch, script_yml, expected_results
    ):
        """
        Given
        - Case 1: deprecated script that is used in none-deprecated playbook, and both deprecated and none-deprecated scripts.
        When
        - Running is_script_deprecated_and_used on the given script.
        Then
        - Ensure the format of the validation is printed out correctly.
        - Case 1: Should print out a list with the name of the given script,
                  and a list of the files paths of the none-deprecated script and playbooks that are using the given script.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        structure = mock_structure(current_file=script_yml)
        validator = ScriptValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        validator.is_script_deprecated_and_used()
        assert str_in_call_args_list(logger_error.call_args_list, expected_results)

    PLAYBOOKS_VALIDATIONS_LS = [
        ({"name": "playbook_case_1", "deprecated": True}, True),
        ({"name": "playbook_case_2", "deprecated": True}, False),
        ({"name": "playbook_case_3", "deprecated": False}, True),
        ({"name": "playbook_case_4", "deprecated": True}, True),
    ]

    @pytest.mark.parametrize("playbook_yml, expected_results", PLAYBOOKS_VALIDATIONS_LS)
    def test_validate_playbook(self, playbook_yml, expected_results):
        """
        Given
        - Case 1: deprecated playbook that isn't being used in any external entities.
        - Case 2: deprecated playbook that is being used in none-deprecated entities.
        - Case 3: none-deprecated playbook that is is being used in both deprecated and none-deprecated sections.
        - Case 4: deprecated playbook that is being used in a deprecated playbook.
        When
        - Running is_playbook_deprecated_and_used on the given playbook.
        Then
        - Ensure validation correctly identifies used deprecated commands in none deprecated entities.
        - Case 1: Should return True.
        - Case 2: Should return False.
        - Case 3: Should return True.
        - Case 4: Should return True.
        """
        structure = mock_structure(current_file=playbook_yml)
        validator = PlaybookValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        assert validator.is_playbook_deprecated_and_used() == expected_results

    PLAYBOOKS_FORMAT_VALIDATIONS = [
        (
            {"name": "playbook_format_case_1", "deprecated": True},
            "[PB120] - playbook_format_case_1 playbook is deprecated and being used by the following entities:\nplaybook_2.yml\n",
        )
    ]

    @pytest.mark.parametrize(
        "playbook_yml, expected_results", PLAYBOOKS_FORMAT_VALIDATIONS
    )
    def test_validate_playbook_error_format(
        self, mocker, monkeypatch, playbook_yml, expected_results
    ):
        """
        Given
        - Case 1: deprecated playbook that is used in a none-deprecated playbook.
        When
        - Running is_playbook_deprecated_and_used on the given playbook.
        Then
        - Ensure the format of the validation is printed out correctly.
        - Case 1: Should print out a list with the name of the given playbook and the file path of the none-deprecated playbook that use it.
        """
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        monkeypatch.setenv("COLUMNS", "1000")

        structure = mock_structure(current_file=playbook_yml)
        validator = PlaybookValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        validator.is_playbook_deprecated_and_used()
        assert str_in_call_args_list(logger_error.call_args_list, expected_results)
