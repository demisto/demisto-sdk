import copy

from demisto_sdk.commands.common.tools import get_yaml
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

        assert integration_detector.check_different()

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

        assert not integration_detector.check_different()

    def test_get_differences(self, pack):

        excepted_result = {
            'parameters': [
                {
                    'type': 'parameters',
                    'name': 'Credentials',
                    'message': "Missing the parameter 'Credentials'."
                },
                {
                    'type': 'parameters',
                    'name': 'API key',
                    'message': "The parameter 'API key' was changed in field 'required'."
                }
            ],
            'commands': [
                {
                    'type': 'commands',
                    'name': 'command_1',
                    'message': "Missing the command 'command_1'."
                }
            ],
            'arguments': [
                {
                    'type': 'arguments',
                    'name': 'argument_2',
                    'command_name': 'command_2',
                    'message': "The argument 'argument_2' in command 'command_2' was changed in field 'isArray'."
                }
            ],
            'outputs': [
                {
                    'type': 'outputs',
                    'name': 'contextPath_2',
                    'command_name': 'command_2',
                    'message': "The output 'contextPath_2' in command 'command_2' was changed in field 'type'."
                }
            ]
        }

        new_integration_yaml = copy.deepcopy(self.NEW_INTEGRATION_YAML)

        # Make some changes in the new integration
        new_integration_yaml['configuration'].remove(new_integration_yaml['configuration'][0])
        new_integration_yaml['configuration'][0]['required'] = 'true'
        new_integration_yaml['script']['commands'].remove(new_integration_yaml['script']['commands'][0])
        new_integration_yaml['script']['commands'][0]['arguments'][1]['isArray'] = 'true'
        new_integration_yaml['script']['commands'][0]['outputs'][1]['type'] = 'String'

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=new_integration_yaml)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        old_integration_yml = get_yaml(old_integration.yml.path)
        new_integration_yml = get_yaml(new_integration.yml.path)

        assert excepted_result == integration_detector.get_differences(old_integration_yml, new_integration_yml)

    def test_get_different_commands(self, pack):
        """
        Given
            - A list of the old integration commands and a list of the new integration commands.
        When
            - Running IntegrationDiffDetector.get_different_commands().
        Then
            - Verify that the function detected the missed old command.
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

        old_commands = self.OLD_INTEGRATION_YAML['script']['commands']
        new_commands = new_integration_yml['script']['commands']

        commands, _, _ = integration_detector.get_different_commands(old_commands, new_commands)

        assert missing_command in commands

    def test_get_different_arguments(self, pack):
        """
        Given
            - A old integration command and a new integration command.
        When
            - Running IntegrationDiffDetector.get_different_arguments().
        Then
            - Verify that the function detect the missed argument and the changed argument.
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
            'message': "The argument 'argument_2' in command 'command_2' was changed in field 'isArray'."
        }

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=self.NEW_INTEGRATION_YAML)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        old_command = self.OLD_INTEGRATION_YAML['script']['commands'][1]
        new_command = new_integration_yml['script']['commands'][1]

        arguments = integration_detector.get_different_arguments(new_command, old_command)

        assert missing_argument in arguments
        assert changed_argument in arguments

    def test_get_different_outputs(self, pack):
        """
        Given
            - A old integration command and a new integration command.
        When
            - Running IntegrationDiffDetector.get_different_outputs().
        Then
            - Verify that the function detect the missed output and the changed output.
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
            'message': "The output 'contextPath_2' in command 'command_2' was changed in field 'type'."
        }

        old_integration = pack.create_integration('oldIntegration', yml=self.OLD_INTEGRATION_YAML)
        new_integration = pack.create_integration('newIntegration', yml=self.NEW_INTEGRATION_YAML)

        integration_detector = IntegrationDiffDetector(new=new_integration.yml.path, old=old_integration.yml.path)

        old_command = self.OLD_INTEGRATION_YAML['script']['commands'][1]
        new_commands = new_integration_yml['script']['commands'][1]
        outputs = integration_detector.get_different_outputs(new_commands, old_command)

        assert missing_output in outputs
        assert changed_output in outputs

    def test_get_different_params(self, pack):
        """
        Given
            - The old integration version params and the new integration version params.
        When
            - Running IntegrationDiffDetector.get_different_params().
        Then
            - Verify that the function detect the missed param and the changed param.
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
        parameters = integration_detector.get_different_params(old_params, new_params)

        assert missing_param in parameters
        assert changed_param in parameters
