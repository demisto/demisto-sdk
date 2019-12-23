from collections import OrderedDict
from argparse import ArgumentDefaultsHelpFormatter

from demisto_sdk.common.tools import print_color, LOG_COLORS
from demisto_sdk.yaml_tools.update_generic_yml import BaseUpdateYML
from demisto_sdk.common.constants import BANG_COMMAND_NAMES


class IntegrationYMLFormat(BaseUpdateYML):
    """PlaybookYMLFormat class is designed to update integration YML file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            yml_data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """
    ARGUMENTS_CORRECT_NAME = {
        'unsecure': 'insecure',
    }

    ARGUMENTS_DESCRIPTION = {
        'insecure': 'Trust any certificate (not secure)',
        'proxy': 'Use system proxy settings'
    }

    def __init__(self, source_file='', output_file_name=''):
        super().__init__(source_file, output_file_name)

    def update_proxy_insecure_param_to_default(self):
        """Updates important integration arguments names and description.
        """
        for integration_argument in self.yml_data.get('configuration', {}):
            argument_name = integration_argument.get('name', '')

            if argument_name in self.ARGUMENTS_CORRECT_NAME:
                argument_name = self.ARGUMENTS_CORRECT_NAME[argument_name]
                integration_argument['name'] = argument_name

            if argument_name in self.ARGUMENTS_DESCRIPTION:
                integration_argument['display'] = self.ARGUMENTS_DESCRIPTION[argument_name]

    def set_reputation_commands_basic_argument_to_default(self):
        """Sets basic arguments of reputation commands to be default.
        """
        integration_commands = self.yml_data.get('script', {}).get('commands', [])

        for command in integration_commands:
            command_name = command.get('name', '')

            if command_name in BANG_COMMAND_NAMES:
                if not (command.get('arguments', []) and command_name not in command['arguments'][0]):
                    command['arguments'] = [
                        {
                            'default': True,
                            'description': '',
                            'isArray': True,
                            'name': command_name,
                            'required': True,
                            'secret': False
                        }
                    ]

                else:
                    command['arguments'][0].update({
                        'default': True,
                        'isArray': True,
                        'required': True
                    })

    def format_file(self):
        """Manager function for the integration YML updater.
        """
        super().update_yml()

        print_color(F'========Starting specific updates for integration: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.update_proxy_insecure_param_to_default()
        self.set_reputation_commands_basic_argument_to_default()
        self.save_yml_to_destination_file()

        print_color(F'========Finished generic updates for integration: {self.output_file_name}=======',
                    LOG_COLORS.YELLOW)

    @staticmethod
    def add_sub_parser(subparsers):
        description = """Run formatter on a given playbook yml file. """
        parser = subparsers.add_parser('format', help=description, formatter_class=ArgumentDefaultsHelpFormatter)
        parser.add_argument("-t", "--type", help="Specify the type of yml file to be formatted.", required=True)
        parser.add_argument("-p", "--path", help="Specify path of playbook yml file", required=True)
        parser.add_argument("-o", "--output-file", help="Specify path where the formatted file will be saved to")
