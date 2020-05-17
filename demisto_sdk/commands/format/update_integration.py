from typing import List, Tuple

from demisto_sdk.commands.common.constants import BANG_COMMAND_NAMES, TYPE_PWSH
from demisto_sdk.commands.common.hook_validations.integration import \
    IntegrationValidator
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class IntegrationYMLFormat(BaseUpdateYML):
    """IntegrationYMLFormat class is designed to update integration YML file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
    """
    ARGUMENTS_DESCRIPTION = {
        'insecure': 'Trust any certificate (not secure)',
        'unsecure': 'Trust any certificate (not secure)',
        'proxy': 'Use system proxy settings'
    }

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '', no_validate: bool = False):
        super().__init__(input, output, path, from_version, no_validate)
        if not from_version and self.data.get("script", {}).get("type") == TYPE_PWSH:
            self.from_version = '5.5.0'

    def update_proxy_insecure_param_to_default(self):
        """Updates important integration arguments names and description."""
        print('Updating proxy and insecure/unsecure integration arguments description to default')

        for integration_argument in self.data.get('configuration', {}):
            argument_name = integration_argument.get('name', '')

            if argument_name in self.ARGUMENTS_DESCRIPTION:
                integration_argument['display'] = self.ARGUMENTS_DESCRIPTION[argument_name]

    def set_reputation_commands_basic_argument_as_needed(self):
        """Sets basic arguments of reputation commands to be default, isArray and required."""
        print('Updating reputation commands\' basic arguments to be True for default, isArray and required')

        integration_commands = self.data.get('script', {}).get('commands', [])

        for command in integration_commands:
            command_name = command.get('name', '')
            current_command_default_argument_changed = False

            if command_name in BANG_COMMAND_NAMES:
                for argument in command.get('arguments', []):
                    if argument.get('name', '') == command_name:
                        argument.update({
                            'default': True,
                            'isArray': True,
                            'required': True
                        })
                        current_command_default_argument_changed = True
                        break

                if not current_command_default_argument_changed:
                    argument_list = command.get('arguments', [])  # type: List
                    argument_list.append(
                        {
                            'default': True,
                            'description': '',
                            'isArray': True,
                            'name': command_name,
                            'required': True,
                            'secret': False
                        }
                    )

                    command['arguments'] = argument_list

    def run_format(self) -> int:
        try:
            super().update_yml()
            self.update_tests()
            self.update_conf_json('integration')
            self.update_proxy_insecure_param_to_default()
            self.set_reputation_commands_basic_argument_as_needed()
            self.save_yml_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception:
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, self.initiate_file_validator(IntegrationValidator)
