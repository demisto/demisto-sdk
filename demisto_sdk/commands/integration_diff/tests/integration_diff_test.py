import copy

from demisto_sdk.commands.integration_diff.integration_diff_detector import (
    IntegrationDiffDetector,
)


class TestIntegrationDiffDetector:

    NEW_INTEGRATION_YAML = {
        "configuration": [
            {
                "display": "Credentials",
                "name": "credentials",
                "required": "true",
                "type": "9",
            },
            {"display": "API key", "name": "api_key", "required": "false", "type": "0"},
            {"display": "URL", "name": "url", "required": "true", "type": "0"},
        ],
        "script": {
            "commands": [
                {
                    "arguments": [
                        {
                            "default": False,
                            "description": "",
                            "isArray": False,
                            "name": "argument",
                            "required": False,
                        }
                    ],
                    "deprecated": False,
                    "description": "",
                    "name": "command_1",
                    "outputs": [
                        {
                            "contextPath": "contextPath_1",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_2",
                            "description": "",
                            "type": "bool",
                        },
                        {
                            "contextPath": "contextPath_3",
                            "description": "",
                            "type": "String",
                        },
                    ],
                },
                {
                    "arguments": [
                        {
                            "default": False,
                            "description": "",
                            "isArray": False,
                            "name": "argument_1",
                            "required": False,
                        },
                        {
                            "default": False,
                            "description": "",
                            "isArray": False,
                            "name": "argument_2",
                            "required": False,
                        },
                    ],
                    "deprecated": False,
                    "description": "",
                    "name": "command_2",
                    "outputs": [
                        {
                            "contextPath": "contextPath_1",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_2",
                            "description": "",
                            "type": "bool",
                        },
                        {
                            "contextPath": "contextPath_3",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_4",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_5",
                            "description": "",
                            "type": "bool",
                        },
                    ],
                },
                {
                    "arguments": [],
                    "deprecated": False,
                    "description": "",
                    "name": "command_3",
                    "outputs": [
                        {
                            "contextPath": "contextPath_1",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_2",
                            "description": "",
                            "type": "bool",
                        },
                        {
                            "contextPath": "contextPath_3",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_4",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_5",
                            "description": "",
                            "type": "bool",
                        },
                        {
                            "contextPath": "contextPath_6",
                            "description": "",
                            "type": "bool",
                        },
                    ],
                },
            ]
        },
    }

    OLD_INTEGRATION_YAML = {
        "configuration": [
            {
                "display": "Credentials",
                "name": "credentials",
                "required": "true",
                "type": "9",
            },
            {"display": "API key", "name": "api_key", "required": "false", "type": "0"},
        ],
        "script": {
            "commands": [
                {
                    "arguments": [
                        {
                            "default": False,
                            "description": "",
                            "isArray": False,
                            "name": "argument",
                            "required": False,
                        }
                    ],
                    "deprecated": False,
                    "description": "",
                    "name": "command_1",
                    "outputs": [
                        {
                            "contextPath": "contextPath_1",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_2",
                            "description": "",
                            "type": "bool",
                        },
                        {
                            "contextPath": "contextPath_3",
                            "description": "",
                            "type": "String",
                        },
                    ],
                },
                {
                    "arguments": [
                        {
                            "default": False,
                            "description": "",
                            "isArray": False,
                            "name": "argument_1",
                            "required": False,
                        },
                        {
                            "default": False,
                            "description": "",
                            "isArray": False,
                            "name": "argument_2",
                            "required": False,
                        },
                    ],
                    "deprecated": False,
                    "description": "",
                    "name": "command_2",
                    "outputs": [
                        {
                            "contextPath": "contextPath_1",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_2",
                            "description": "",
                            "type": "bool",
                        },
                        {
                            "contextPath": "contextPath_3",
                            "description": "",
                            "type": "String",
                        },
                        {
                            "contextPath": "contextPath_4",
                            "description": "",
                            "type": "String",
                        },
                    ],
                },
            ]
        },
    }

    DIFFERENCES_REPORT = {
        "parameters": [
            {
                "type": "parameters",
                "name": "Credentials",
                "message": "Missing the parameter 'Credentials'.",
            },
            {
                "type": "parameters",
                "name": "API key",
                "message": "The parameter `API key` - Is now required.",
                "changed_field": "required",
                "changed_value": "true",
            },
        ],
        "commands": [
            {
                "description": "",
                "type": "commands",
                "name": "command_1",
                "message": "Missing the command 'command_1'.",
            }
        ],
        "arguments": [
            {
                "type": "arguments",
                "name": "argument_2",
                "command_name": "command_2",
                "message": "The argument `argument_2` in the command `command_2` - Now supports comma separated values.",
                "changed_field": "isArray",
                "changed_value": "true",
            }
        ],
        "outputs": [
            {
                "type": "outputs",
                "name": "contextPath_2",
                "command_name": "command_2",
                "message": "The output 'contextPath_2' in the command 'command_2' was changed in field 'type'.",
                "changed_field": "type",
            }
        ],
    }

    def test_valid_integration_diff(self, pack):
        """
        Given
            - Two integrations of a pack.
        When
            - Running check_diff().
        Then
            - Ensure the integrations are backwards compatible.
        """

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        assert integration_detector.check_different()

    def test_invalid_integration_diff(self, pack):
        """
        Given
            - Two integrations of a pack, when the new version are not backward compatible.
        When
            - Running check_diff().
        Then
            - Ensure the integrations are not backwards compatible.
        """

        old_integration = pack.create_integration(
            "oldIntegration2", yml=self.NEW_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration2", yml=self.OLD_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        assert not integration_detector.check_different()

    def test_get_differences(self, pack):
        """
        Given
            - Two integration yaml data, when the new version are not backward compatible.
        When
            - Running get_differences().
        Then
            - Verify the result as excepted.
        """
        new_integration_yaml = copy.deepcopy(self.NEW_INTEGRATION_YAML)

        # Make some changes in the new integration
        new_integration_yaml["configuration"].remove(
            new_integration_yaml["configuration"][0]
        )
        new_integration_yaml["configuration"][0]["required"] = "true"
        new_integration_yaml["script"]["commands"].remove(
            new_integration_yaml["script"]["commands"][0]
        )
        new_integration_yaml["script"]["commands"][0]["arguments"][1][
            "isArray"
        ] = "true"
        new_integration_yaml["script"]["commands"][0]["outputs"][1]["type"] = "String"

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=new_integration_yaml
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )
        differences = integration_detector.get_differences()

        assert self.DIFFERENCES_REPORT == differences

    def test_get_different_commands(self, pack):
        """
        Given
            - A list of the old integration commands and a list of the new integration commands.
        When
            - Running get_different_commands().
        Then
            - Verify that the function detected the missed old command.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml["script"]["commands"].remove(
            new_integration_yml["script"]["commands"][0]
        )

        missing_command = {
            "description": "",
            "type": "commands",
            "name": "command_1",
            "message": "Missing the command 'command_1'.",
        }

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        old_commands = self.OLD_INTEGRATION_YAML["script"]["commands"]
        new_commands = new_integration_yml["script"]["commands"]

        commands, _, _ = integration_detector.get_different_commands(
            old_commands, new_commands
        )

        assert missing_command in commands

    def test_get_different_arguments(self, pack):
        """
        Given
            - A old integration command and a new integration command.
        When
            - Running get_different_arguments().
        Then
            - Verify that the function detect the missed argument and the changed argument.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml["script"]["commands"][1]["arguments"].remove(
            new_integration_yml["script"]["commands"][1]["arguments"][0]
        )
        new_integration_yml["script"]["commands"][1]["arguments"][0]["isArray"] = True

        missing_argument = {
            "type": "arguments",
            "name": "argument_1",
            "command_name": "command_2",
            "message": "Missing the argument 'argument_1' in the command 'command_2'.",
        }

        changed_argument = {
            "type": "arguments",
            "name": "argument_2",
            "command_name": "command_2",
            "message": "The argument `argument_2` in the command `command_2` - Now supports comma separated values.",
            "changed_field": "isArray",
            "changed_value": True,
        }

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        old_command = self.OLD_INTEGRATION_YAML["script"]["commands"][1]
        new_command = new_integration_yml["script"]["commands"][1]

        arguments = integration_detector.get_different_arguments(
            new_command, old_command
        )

        assert missing_argument in arguments
        assert changed_argument in arguments

    def test_get_different_outputs(self, pack):
        """
        Given
            - A old integration command and a new integration command.
        When
            - Running get_different_outputs().
        Then
            - Verify that the function detect the missed output and the changed output.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml["script"]["commands"][1]["outputs"].remove(
            new_integration_yml["script"]["commands"][1]["outputs"][0]
        )
        new_integration_yml["script"]["commands"][1]["outputs"][0]["type"] = "String"

        missing_output = {
            "type": "outputs",
            "name": "contextPath_1",
            "command_name": "command_2",
            "message": "Missing the output 'contextPath_1' in the command 'command_2'.",
        }

        changed_output = {
            "type": "outputs",
            "name": "contextPath_2",
            "command_name": "command_2",
            "message": "The output 'contextPath_2' in the command 'command_2' was changed in field 'type'.",
            "changed_field": "type",
        }

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        old_command = self.OLD_INTEGRATION_YAML["script"]["commands"][1]
        new_commands = new_integration_yml["script"]["commands"][1]
        outputs = integration_detector.get_different_outputs(new_commands, old_command)

        assert missing_output in outputs
        assert changed_output in outputs

    def test_get_different_params(self, pack):
        """
        Given
            - The old integration version params and the new integration version params.
        When
            - Running get_different_params().
        Then
            - Verify that the function detect the missed param and the changed param.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml["configuration"].remove(
            new_integration_yml["configuration"][0]
        )
        new_integration_yml["configuration"][0]["required"] = "true"

        missing_param = {
            "type": "parameters",
            "name": "Credentials",
            "message": "Missing the parameter 'Credentials'.",
        }

        changed_param = {
            "type": "parameters",
            "name": "API key",
            "message": "The parameter `API key` - Is now required.",
            "changed_field": "required",
            "changed_value": "true",
        }

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=new_integration_yml
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        old_params = self.OLD_INTEGRATION_YAML["configuration"]
        new_params = new_integration_yml["configuration"]
        parameters = integration_detector.get_different_params(old_params, new_params)

        assert missing_param in parameters
        assert changed_param in parameters

    def test_print_without_items(self, pack, capsys):
        """
        Given
            - Two integration versions when the new version are backward compatible .
        When
            - Running print_items().
        Then
            - Verify there are no items to print and that the printed output as excepted.
        """

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        assert not integration_detector.print_items()

        captured = capsys.readouterr()
        assert "The integrations are backwards compatible" in captured.out

    def test_print_items(self, pack, capsys):
        """
        Given
            - Dict contains all the differences between two integration versions.
        When
            - Running print_items().
        Then
            - Verify that.
        """

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        integration_detector.missing_items_report = copy.deepcopy(
            self.DIFFERENCES_REPORT
        )

        assert integration_detector.print_items()

    def test_print_missing_items(self, pack, capsys):
        """
        Given
            - Missing items to print.
        When
            - Running print_missing_items().
        Then
            - Verify that all the items are printed.
        """

        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path
        )

        integration_detector.missing_items_report = copy.deepcopy(
            self.DIFFERENCES_REPORT
        )

        integration_detector.print_missing_items()

        excepted_output = (
            "Missing parameters:\n\nMissing the parameter 'Credentials'.\n\nChanged parameters:\n\n"
            "The parameter `API key` - Is now required.\n\nMissing commands:\n\nMissing the command "
            "'command_1'.\n\nMissing arguments:\n\n\nChanged arguments:\n\nThe argument `argument_2` "
            "in the command `command_2` - Now supports comma separated values.\n\nMissing outputs:"
            "\n\n\nChanged outputs:\n\nThe output 'contextPath_2' in the command 'command_2' was "
            "changed in field 'type'.\n\n"
        )

        captured = capsys.readouterr()
        assert excepted_output in captured.out

    def test_print_items_in_docs_format(self, pack, capsys, mocker):
        """
        Given
            - Missing items to print in docs format.
        When
            - Running print_missing_items().
        Then
            - Verify that all the items are printed in docs format.
        """
        old_integration = pack.create_integration(
            "oldIntegration", yml=self.OLD_INTEGRATION_YAML
        )
        new_integration = pack.create_integration(
            "newIntegration", yml=self.NEW_INTEGRATION_YAML
        )

        integration_detector = IntegrationDiffDetector(
            new=new_integration.yml.path, old=old_integration.yml.path, docs_format=True
        )

        integration_detector.missing_items_report = copy.deepcopy(
            self.DIFFERENCES_REPORT
        )

        integration_detector.print_items_in_docs_format()

        excepted_output = (
            "\n## Breaking changes from the previous version of this integration - \n"
            "The following sections list the changes in this version.\n\n### Commands\n"
            "#### The following commands were removed in this version:\n* *command_1* - this command "
            "was replaced by XXX.\n\n### Arguments\n"
            "#### The behavior of the following arguments was changed:\n\nIn the *command_2* command:\n"
            "* *argument_2* - Now supports comma separated values.\n\n### Outputs\n"
            "#### The following outputs were removed in this version:\n\n## Additional Considerations for"
            " this version\n* Insert any API changes, any behavioral changes, limitations, "
            "or restrictions that would be new to this version.\n\n"
        )
        captured = capsys.readouterr()
        assert excepted_output in captured.out
