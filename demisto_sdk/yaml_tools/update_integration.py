from copy import deepcopy

from demisto_sdk.yaml_tools.update_generic_yml import BaseUpdateYML
from demisto_sdk.common.constants import BANG_COMMAND_NAMES, DBOT_SCORES_DICT


class IntegrationYMLFormat(BaseUpdateYML):
    """PlaybookYMLFormat class is designed to update integration YML file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            yml_data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """
    ARGUMENTS_CORRECT_POSSIBLE_DESCRIPTION = {
        # Dict. [possible_names_given]: [desired_name, desired_description]
        ['insecure', 'unsecure']: ['insecure', 'Trust any certificate (not secure)'],
        ['proxy']: ['proxy', 'Use system proxy settings']
    }

    def __init__(self, source_file='', output_file_name=''):
        super().__init__(source_file, output_file_name)

    def update_proxy_insecure_param_to_default(self):
        """Updates important integration arguments names and description.
        """
        integration_configuration_dict = self.yml_data.get('configuration', {})
        for arguments_list in self.ARGUMENTS_CORRECT_POSSIBLE_DESCRIPTION:
            for argument in arguments_list:
                if argument in integration_configuration_dict:
                    del integration_configuration_dict[argument]

                    desired_argument_name_and_description = self.ARGUMENTS_CORRECT_POSSIBLE_DESCRIPTION[arguments_list]
                    integration_configuration_dict[desired_argument_name_and_description[0]] = \
                        desired_argument_name_and_description[1]

    def set_reputation_commands_basic_argument_to_default(self):
        """Sets basic arguments of reputation commands to be default.
        """
        integration_commands = self.yml_data.get('script', {}).get('commands', [])
        for command in integration_commands:
            command_name = command.get('name', '')
            if command_name in BANG_COMMAND_NAMES:
                if command_name in command['arguments']:
                    command['arguments']['default'] = True
                else:
                    command.get('arguments').appemd(
                        [
                            ('default', True),
                            ('description', ''),
                            ('isArray', True),
                            ('name', command_name),
                            ('required', True),
                            ('secret', False)
                        ]
                    )

    def set_reputation_commands_dbot_context_paths(self):
        """Sets the DBot context paths for reputation commands.
        """
        dbot_dict_copy = deepcopy(DBOT_SCORES_DICT)

        integration_commands = self.yml_data.get('script', {}).get('commands', [])
        for command in integration_commands:
            if command.get('name', '') in BANG_COMMAND_NAMES:
                outputs_exists = command.get('outputs')
                for context_path in outputs_exists:
                    for dbot_context_path in DBOT_SCORES_DICT:
                        if dbot_context_path in context_path:
                            context_path['description'] = DBOT_SCORES_DICT[dbot_context_path]

                            if dbot_context_path == 'DBotScore.Score':
                                context_path['type'] = 'Number'
                            else:
                                context_path['type'] = 'String'

                            del dbot_dict_copy[dbot_context_path]

                for dbot_path_not_in_outputs in dbot_dict_copy.keys():
                    outputs_exists.append(
                        [
                            ('contextPath', dbot_path_not_in_outputs),
                            ('description', DBOT_SCORES_DICT[dbot_path_not_in_outputs]),
                            ('type', 'String') if dbot_path_not_in_outputs != 'DBotScore.Score' else ('type', 'Number')
                        ]
                    )
