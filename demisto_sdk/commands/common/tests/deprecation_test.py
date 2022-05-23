import pytest

from demisto_sdk.commands.common.hook_validations.deprecation import \
    DeprecationValidator
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.hook_validations.script import ScriptValidator
from demisto_sdk.commands.common.tests.integration_test import mock_structure

mocked_id_set = {"scripts": [
    {"sdca13-dasde12-ffe13-fdgs352": {
        "name": "script_1",
        "file_path": "script_1.yml",
        "deprecated": True,
        "depends_on": [
            "ic3_command1",
            "ic5_command1",
            "ic6_command3",
            "script_case_4",
            "script_case_7"
        ]
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
                "script_case_3"
            ]
        }
    }], "playbooks": [
    {"sdca13-dasde12-ffe13-fdgs3541": {
        "name": "playbook_1",
        "file_path": "playbook_1.yml",
        "deprecated": True,
        "implementing_scripts": [
            "IsIntegrationAvailable"
        ],
        "implementing_playbooks": [
            "GenericPolling"
        ],
        "command_to_integration": {
            "ic3_command1": [
                "integration_case_3"
            ],
            "ic6_command2": [
                "integration_case_6"
            ]
        }}},
        {"sdca13-dasde12-ffe13-fdgs35as": {
            "name": "playbook_4",
            "file_path": "playbook_4.yml",
            "implementing_scripts": [
                "script_case_2",
                "script_case_7"
            ],
            "implementing_playbooks": [
                "GenericPolling"
            ],
            "command_to_integration": {
                "ic2_command1": [
                    "integration_case_2"
                ],
                "ic5_command2": [
                    "integration_case_5"
                ],
                "ic6_command1": [
                    "integration_case_6"
                ]
            }}}
],
    "TestPlaybooks": [
    {"sdca13-dasde12-ffe13-fdgs3541": {
        "name": "testplaybook_1",
        "file_path": "testplaybook_1.yml",
        "deprecated": True,
        "implementing_scripts": [
            "script_case_5"
        ],
        "implementing_playbooks": [
            "GenericPolling"
        ]}},
        {"sdca13-dasde12-ffe13-fdgs35as": {
            "name": "testplaybook_2",
            "file_path": "testplaybook_2.yml",
            "implementing_scripts": [
                "script_case_6"
            ],
            "implementing_playbooks": [
                "GenericPolling"
            ]}}
]
}


def mock_deprecation_manager():
    # type: () -> DeprecationValidator
    deprecation_validator = DeprecationValidator(mocked_id_set)
    return deprecation_validator


class TestDeprecationValidator:

    INTEGRATIONS_VALIDATIONS_LS = [({'name': "integration_case_1", 'deprecated': True, 'script': {'commands': [{'name': 'ic1_command1'}]}},
                                    False, ["ic1_command1"], []),
                                   ({'name': "integration_case_2", 'script': {'commands': [
                                    {'name': 'ic2_command1', 'deprecated': True}]}}, False, ["ic2_command1"], []),
                                   ({'name': "integration_case_3", 'script': {'commands': [
                                    {'name': 'ic3_command1', 'deprecated': True}]}}, True, [], ["ic3_command1"]),
                                   ({'name': "integration_case_4", 'deprecated': False, 'script': {
                                    'commands': [{'name': 'ic4_command1'}]}}, True, [], ["ic4_command1"]),
                                   ({'name': "integration_case_5", 'deprecated': False, 'script': {'commands': [
                                    {'name': 'ic5_command1', 'deprecated': True}, {'name': 'ic5_command2'}]}}, True, [], ["ic5_command1", "ic5_command2"]),
                                   ({'name': "integration_case_6", 'script': {'commands': [{'name': 'ic6_command1', 'deprecated': True}, {
                                    'name': 'ic6_command2', 'deprecated': True}, {'name': 'ic6_command3'}]}},
                                    False, ["ic6_command1"], ["ic6_command3", "ic6_command2"]),
                                   ]

    @pytest.mark.parametrize("integration_yml, expected_bool_results, expected_commands_in_errors_ls, expected_commands_not_in_errors_ls",
                             INTEGRATIONS_VALIDATIONS_LS)
    def test_validate_integration(self, capsys, integration_yml, expected_bool_results, expected_commands_in_errors_ls, expected_commands_not_in_errors_ls):
        """
        Given
        - Case 1: integration with one deprecated command that is being used in a none-deprecated script.
        - Case 2: integration with one deprecated command that is being used in a none-deprecated playbook.
        - Case 3: integration with one deprecated command that is being used only in deprecated entities.
        - Case 4: integration with one none-deprecated command that is being used in both deprecated and none-deprecated entities.
        - Case 5: A deprecated integration with two commands, one deprecated and one none-dreprecated:
                  the none-deprecated is being used in none-deprecated entities only,
                  and the deprecated is being used in deprecated entities only.
        - Case 6: Integration with two deprecated commands and one none-deprecated command,
                  one deprecated is being used in deprecated entities only,
                  one deprecated is being used in none-deprecated entities only,
                  and the none-deprecated is being used in both deprecated and none-deprecated entities.
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
        """
        structure = mock_structure(current_file=integration_yml)
        validator = IntegrationValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        bool_result = validator.is_integration_deprecated_and_used()
        assert bool_result == expected_bool_results
        stdout = capsys.readouterr().out
        for command in expected_commands_in_errors_ls:
            assert command in stdout
        for command in expected_commands_not_in_errors_ls:
            assert command not in stdout

    SCRIPTS_VALIDATIONS_LS = [({'name': "script_case_1", 'deprecated': True}, True),
                              ({'name': "script_case_2", 'deprecated': True}, False),
                              ({'name': "script_case_3", 'deprecated': True, 'tests': []}, False),
                              ({'name': "script_case_4", 'deprecated': True, 'tests': ["No Tests"] }, True),
                              ({'name': "script_case_5", 'deprecated': True, 'tests': ["testplaybook_1"] }, True),
                              ({'name': "script_case_6", 'deprecated': True, 'tests': ["testplaybook_2"] }, False),
                              ({'name': "script_case_7", 'deprecated': False}, True)
                              ]

    @pytest.mark.parametrize("script_yml, expected_results", SCRIPTS_VALIDATIONS_LS)
    def test_validate_script(self, script_yml, expected_results):
        """
        Given
        - Case 1: deprecated script that isn't being used in any external entities.
        - Case 2: deprecated script that is being used in none-deprecated entities.
        - Case 3: deprecated script with empty tests section that is being used in a none-deprecated script.
        - Case 4: deprecated script with "No Tests" in the tests section that is being used in a deprecated script.
        - Case 5: deprecated script with one deprecated test in the tests section.
        - Case 6: deprecated script with one none-deprecated test in the tests section.
        - Case 7: none-deprecated script that is is being used in both deprecated and none-deprecated sections.
        When
        - Running is_script_deprecated_and_used on the given script.
        Then
        - Ensure validation correctly identifies used deprecated commands in none deprecated entities.
        - Case 1: Should return True.
        - Case 2: Should return False.
        - Case 3: Should return False.
        - Case 4: Should return False.
        - Case 5: Should return True.
        - Case 6: Should return True.
        """
        structure = mock_structure(current_file=script_yml)
        validator = ScriptValidator(structure)
        validator.deprecation_validator = mock_deprecation_manager()
        assert validator.is_script_deprecated_and_used() == expected_results
