import os

import click
from demisto_sdk.commands.common.constants import (ARGUMENT_FIELDS_TO_CHECK,
                                                   PARAM_FIELDS_TO_CHECK)
from demisto_sdk.commands.common.tools import get_yaml


class IntegrationDiffDetector:

    def __init__(self, new: str = '', old: str = ''):

        if not os.path.exists(new):
            click.secho('No such file or directory for the new integration.', fg='bright_red')

        if not os.path.exists(old):
            click.secho('No such file or directory for the old integration.', fg='bright_red')

        self.new = new
        self.old = old

        self.fount_missing = False
        self.missing_details_report: dict = {
            'parameters': [],
            'commands': [],
            'arguments': [],
            'outputs': []
        }

    def check_diff(self) -> bool:
        """
        Checks differences between two integration yaml files.

        Return:
            bool. return true if the new integration contains everything in the old integration.
        """
        old_yaml_data = get_yaml(self.old)
        new_yaml_data = get_yaml(self.new)

        old_commands_data = old_yaml_data['script']['commands']
        new_commands_data = new_yaml_data['script']['commands']

        # for each old integration command check if exist in the new, if not, check what is missing
        for old_command in old_commands_data:
            if old_command not in new_commands_data:
                self.check_command(old_command, new_commands_data)

        self.check_params(old_yaml_data['configuration'], new_yaml_data['configuration'])

        if self.print_missing_items():
            return False
        return True

    def check_command(self, old_command, new_commands):
        """
        Checks a specific old integration command and it's arguments and outputs if exist in the new integration

        Args:
            old_command: The command of the old integration.
            new_commands: List of the new integration commands
        """

        new_command = IntegrationDiffDetector.check_if_element_exist(old_command, new_commands, 'name')

        if not new_command:
            self.add_changed_item(item_type='commands', item_name=old_command['name'],
                                  message=f'Missing the command \'{old_command["name"]}\'.')
        else:
            # Gets all the fields that are different between the two commands
            changed_fields = [field for field in new_command if field in old_command and
                              new_command[field] != old_command[field]]

            if 'arguments' in changed_fields:
                self.check_command_arguments(new_command, old_command)

            if 'outputs' in changed_fields:
                self.check_command_outputs(new_command, old_command)

    def check_command_arguments(self, new_command, old_command):
        """
        Checks the old integration command arguments if exists in the new integration command

        Args:
            new_command: The new integration command.
            old_command: The old integration command.
        """

        new_command_arguments = new_command['arguments']
        old_command_arguments = old_command['arguments']

        for argument in old_command_arguments:
            if argument not in new_command_arguments:

                new_command_argument = IntegrationDiffDetector.check_if_element_exist(argument, new_command_arguments,
                                                                                      'name')

                if not new_command_argument:
                    self.add_changed_item(item_type='arguments', item_name=argument['name'],
                                          message=f'Missing the argument \'{argument["name"]}\' in command '
                                                  f'\'{new_command["name"]}\'.', command_name=new_command['name'])
                else:
                    # Gets all the fields that are different between the two arguments
                    changed_fields = [field for field in new_command_argument if field in argument and
                                      new_command_argument[field] != argument[field]]

                    self.check_changed_fields(element=new_command_argument, element_type='arguments',
                                              fields_to_check=ARGUMENT_FIELDS_TO_CHECK, changed_fields=changed_fields,
                                              command=new_command)

    def check_changed_fields(self, element, element_type, fields_to_check, changed_fields, command=None):
        """
        Checks for changed fields in a given element.

        Args:
            element: The element to check.
            element_type: The element type.
            fields_to_check: List of fields to check if changed.
            changed_fields: List of changed fields.
            command: The command to check his argument.
        """

        for field in fields_to_check:

            if field in changed_fields:

                if (field == 'required' or field == 'isArray') and not element[field]:
                    continue

                if element_type == 'arguments':

                    self.add_changed_item(item_type=element_type, item_name=element['name'],
                                          message=f'The argument \'{element["name"]}\' in command \'{command["name"]}\''
                                                  f' was changed in field {field}.', command_name=command["name"])

                elif element_type == 'params':

                    self.add_changed_item(item_type=element_type, item_name=element['display'],
                                          message=f'The parameter \'{element["display"]}\' was changed in field {field}.')

    def check_command_outputs(self, new_command, old_command):
        """
        Checks the old integration command outputs if exists in the new integration command.

        Args:
            new_command: The new integration command.
            old_command: The old integration command.
        """

        new_command_outputs = new_command['outputs']
        old_command_outputs = old_command['outputs']

        for output in old_command_outputs:
            if output not in new_command_outputs:

                new_command_output = IntegrationDiffDetector.check_if_element_exist(output, new_command_outputs,
                                                                                    'contextPath')

                if not new_command_output:
                    self.add_changed_item(item_type='outputs', item_name=output['contextPath'],
                                          message=f'Missing the output \'{output["contextPath"]}\' in command '
                                                  f'\'{new_command["name"]}\'.', command_name=new_command['name'])

                else:
                    # Gets all the fields that are different between the two outputs
                    changed_fields = [field for field in new_command_output if field in output and
                                      new_command_output[field] != output[field]]

                    if 'type' in changed_fields:
                        self.add_changed_item(item_type='outputs', item_name=output['contextPath'],
                                              message=f'The output \'{output["contextPath"]}\' type in command '
                                                      f'\'{new_command["name"]}\' was changed.',
                                              command_name=new_command["name"])

    def check_params(self, old_params, new_params):
        """
        Checks the old integration params if exists in the new integration.

        Args:
            old_params: The old integration parameters.
            new_params: The new integration parameters.
        """

        for old_param in old_params:

            if old_param not in new_params:

                param = self.check_if_element_exist(old_param, new_params, 'display')

                if not param:
                    self.add_changed_item(item_type='parameters', item_name=old_param['display'],
                                          message=f'Missing the parameter {old_param["display"]}')

                else:
                    # Gets all the fields that are different between the two params
                    changed_fields = [field for field in param if field in old_param and
                                      param[field] != old_param[field]]

                    self.check_changed_fields(element=param, element_type='parameters',
                                              fields_to_check=PARAM_FIELDS_TO_CHECK, changed_fields=changed_fields)

    def add_changed_item(self, item_type, item_name, message, command_name=''):
        """
        Added the missing item to the report list to print

        Args:
            item_type: The item type (command/argument/output).
            item_name: The name of the item.
            message: The message to print.
            command_name: If the type is argument/output, then we get the command name that the item is missing.
        """

        item = {
            'type': item_type,
            'name': item_name
        }

        if item_type != 'commands' and command_name:
            item['command_name'] = command_name

        item['message'] = message

        self.missing_details_report[item_type].append(item)
        self.fount_missing = True

    @staticmethod
    def check_if_element_exist(element_to_check, list_of_elements, field_to_check) -> dict:
        """
        Check if a given element exists in a given list.

        Args:
            element_to_check: The element to check.
            list_of_elements: The list of elements.
            field_to_check: The field being checked.

        Return:
            The element if exist and an empty dict if not.
        """

        for element in list_of_elements:

            if element[field_to_check] == element_to_check[field_to_check]:
                return element

        return {}

    def print_missing_items(self) -> bool:
        """
        Prints the missing elements report.

        Return:
            bool. return true if found items to print and false if not.
        """

        if not self.fount_missing:
            click.secho("The integrations are backwards compatible", fg='green')
            return False

        for missing_type in self.missing_details_report:
            if self.missing_details_report[missing_type]:
                click.secho(f"\nMissing {missing_type}:\n", fg='bright_red')

                for item in self.missing_details_report[missing_type]:
                    click.secho(item['message'] + "\n", fg='bright_red')
        return True
