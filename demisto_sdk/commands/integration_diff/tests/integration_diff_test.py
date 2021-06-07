import copy

from demisto_sdk.commands.integration_diff.integration_diff_detector import \
    IntegrationDiffDetector


class TestIntegrationDiffDetector:

    NEW_INTEGRATION_YAML = {
        'configuration': [
            {
                'display': 'Credentials',
                'name': 'credentials',
                'required': 'true',
                'type': '9'
            },
            {
                'display': 'API key',
                'name': 'api_key',
                'required': 'false',
                'type': '0'
            },
            {
                'display': 'URL',
                'name': 'url',
                'required': 'true',
                'type': '0'
            }
        ],
        'script': {
            'commands': [
                {
                    'arguments': [
                        {
                            'default': False,
                            'description': '',
                            'isArray': False,
                            'name': 'argument',
                            'required': False
                        }
                    ],
                    'deprecated': False,
                    'description': '',
                    'name': 'command_1',
                    'outputs': [
                        {'contextPath': 'contextPath_1', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_2', 'description': '', 'type': 'bool'},
                        {'contextPath': 'contextPath_3', 'description': '', 'type': 'String'},
                    ]
                },
                {
                    'arguments': [
                        {
                            'default': False,
                            'description': '',
                            'isArray': False,
                            'name': 'argument_1',
                            'required': False
                        },
                        {
                            'default': False,
                            'description': '',
                            'isArray': False,
                            'name': 'argument_2',
                            'required': False
                        }
                    ],
                    'deprecated': False,
                    'description': '',
                    'name': 'command_2',
                    'outputs': [
                        {'contextPath': 'contextPath_1', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_2', 'description': '', 'type': 'bool'},
                        {'contextPath': 'contextPath_3', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_4', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_5', 'description': '', 'type': 'bool'}
                    ]
                },
                {
                    'arguments': [],
                    'deprecated': False,
                    'description': '',
                    'name': 'command_3',
                    'outputs': [
                        {'contextPath': 'contextPath_1', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_2', 'description': '', 'type': 'bool'},
                        {'contextPath': 'contextPath_3', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_4', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_5', 'description': '', 'type': 'bool'},
                        {'contextPath': 'contextPath_6', 'description': '', 'type': 'bool'}
                    ]
                }
            ]
        }
    }

    OLD_INTEGRATION_YAML = {
        'configuration': [
            {
                'display': 'Credentials',
                'name': 'credentials',
                'required': 'true',
                'type': '9'
            },
            {
                'display': 'API key',
                'name': 'api_key',
                'required': 'false',
                'type': '0'
            }
        ],
        'script': {
            'commands': [
                {
                    'arguments': [
                        {
                            'default': False,
                            'description': '',
                            'isArray': False,
                            'name': 'argument',
                            'required': False
                        }
                    ],
                    'deprecated': False,
                    'description': '',
                    'name': 'command_1',
                    'outputs': [
                        {'contextPath': 'contextPath_1', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_2', 'description': '', 'type': 'bool'},
                        {'contextPath': 'contextPath_3', 'description': '', 'type': 'String'},
                    ]
                },
                {
                    'arguments': [
                        {
                            'default': False,
                            'description': '',
                            'isArray': False,
                            'name': 'argument_1',
                            'required': False
                        },
                        {
                            'default': False,
                            'description': '',
                            'isArray': False,
                            'name': 'argument_2',
                            'required': False
                        }
                    ],
                    'deprecated': False,
                    'description': '',
                    'name': 'command_2',
                    'outputs': [
                        {'contextPath': 'contextPath_1', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_2', 'description': '', 'type': 'bool'},
                        {'contextPath': 'contextPath_3', 'description': '', 'type': 'String'},
                        {'contextPath': 'contextPath_4', 'description': '', 'type': 'String'},
                    ]
                }
            ]
        }
    }

    def test_valid_integration_diff(self, pack):
        """
        Given
            - Two integrations of a pack.
        When
            - Running IntegrationDiffDetector.check_diff().
        Then
            - Ensure the integrations are backwards compatible.
        """

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=self.NEW_INTEGRATION_YAML)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        assert integration_detector.check_diff()

    def test_invalid_integration_diff(self, pack):
        """
        Given
            - Two integrations of a pack, when the new version are not backward compatible.
        When
            - Running IntegrationDiffDetector.check_diff().
        Then
            - Ensure the integrations are not backwards compatible.
        """

        old_integration = pack.create_integration('oldIntegration2', yml=self.NEW_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration2', yml=self.OLD_INTEGRATION_YAML)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        assert not integration_detector.check_diff()

    def test_check_command(self, pack):
        """
        Given
            - A old version command and a list of new version commands.
        When
            - Running IntegrationDiffDetector.check_command().
        Then
            - Verify that the function detected that the old command is missing.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml['script']['commands'].remove(new_integration_yml['script']['commands'][0])

        missing_command = {
            'type': 'commands',
            'name': 'command_1',
            'message': "Missing the command 'command_1'."
        }

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=self.NEW_INTEGRATION_YAML)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        old_command = self.OLD_INTEGRATION_YAML['script']['commands'][0]
        new_commands = new_integration_yml['script']['commands']
        integration_detector.check_command(old_command, new_commands)

        assert missing_command in integration_detector.missing_details_report['commands']

    def test_check_command_arguments(self, pack):
        """
        Given
            - A old version command and a new version command.
        When
            - Running IntegrationDiffDetector.check_command_arguments().
        Then
            - Verify that the function detected that one argument is missing and that one argument changed.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml['script']['commands'][1]['arguments'].remove(new_integration_yml['script']['commands'][1]
                                                                         ['arguments'][0])
        new_integration_yml['script']['commands'][1]['arguments'][0]['isArray'] = True

        missing_argument = {
            'type': 'arguments',
            'name': 'argument_1',
            'command_name': 'command_2',
            'message': "Missing the argument 'argument_1' in command 'command_2'."
        }

        changed_argument = {
            'type': 'arguments',
            'name': 'argument_2',
            'command_name': 'command_2',
            'message': "The argument 'argument_2' in command 'command_2' was changed in field isArray."
        }

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=self.NEW_INTEGRATION_YAML)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        old_command = self.OLD_INTEGRATION_YAML['script']['commands'][1]
        new_command = new_integration_yml['script']['commands'][1]
        integration_detector.check_command_arguments(new_command, old_command)

        assert missing_argument in integration_detector.missing_details_report['arguments']
        assert changed_argument in integration_detector.missing_details_report['arguments']

    def test_check_command_outputs(self, pack):
        """
        Given
            - A old version command and a new version command.
        When
            - Running IntegrationDiffDetector.check_command_outputs().
        Then
            - Verify that the function detected that one output is missing and that one output changed.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml['script']['commands'][1]['outputs'].remove(new_integration_yml['script']['commands'][1]
                                                                       ['outputs'][0])
        new_integration_yml['script']['commands'][1]['outputs'][0]['type'] = 'String'

        missing_output = {
            'type': 'outputs',
            'name': 'contextPath_1',
            'command_name': 'command_2',
            'message': "Missing the output 'contextPath_1' in command 'command_2'."
        }

        changed_output = {
            'type': 'outputs',
            'name': 'contextPath_2',
            'command_name': 'command_2',
            'message': "The output 'contextPath_2' type in command 'command_2' was changed."
        }

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=self.NEW_INTEGRATION_YAML)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        old_command = self.OLD_INTEGRATION_YAML['script']['commands'][1]
        new_commands = new_integration_yml['script']['commands'][1]
        integration_detector.check_command_outputs(new_commands, old_command)

        assert missing_output in integration_detector.missing_details_report['outputs']
        assert changed_output in integration_detector.missing_details_report['outputs']

    def test_check_params(self, pack):
        """
        Given
            - The old integration version params and the new integration version params.
        When
            - Running IntegrationDiffDetector.check_params().
        Then
            - Verify that the function detected that one param is missing and that one param changed.
        """

        new_integration_yml = copy.deepcopy(self.NEW_INTEGRATION_YAML)
        new_integration_yml['configuration'].remove(new_integration_yml['configuration'][0])
        new_integration_yml['configuration'][0]['required'] = 'true'

        missing_param = {
            'type': 'parameters',
            'name': 'Credentials',
            'message': "Missing the parameter 'Credentials'."
        }

        changed_param = {
            'type': 'parameters',
            'name': 'API key',
            'message': "The parameter 'API key' was changed in field 'required'."
        }

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=new_integration_yml)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        old_params = self.OLD_INTEGRATION_YAML['configuration']
        new_params = new_integration_yml['configuration']
        integration_detector.check_params(old_params, new_params)

        assert missing_param in integration_detector.missing_details_report['parameters']
        assert changed_param in integration_detector.missing_details_report['parameters']
