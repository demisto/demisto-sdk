import os

import click
from demisto_sdk.commands.common.constants import (ARGUMENT_FIELDS_TO_CHECK,
                                                   PARAM_FIELDS_TO_CHECK)
from demisto_sdk.commands.common.tools import get_yaml


class IntegrationDiffDetector:

    def __init__(self, new: str = '', old: str = '', docs_format: bool = False):

        if not os.path.exists(new):
            click.secho('No such file or directory for the new integration.', fg='bright_red')

        if not os.path.exists(old):
            click.secho('No such file or directory for the old integration.', fg='bright_red')

        self.new = new
        self.old = old
        self.docs_format_output = docs_format

        self.fount_missing = False
        self.missing_items_report: dict = {}

    def check_different(self) -> bool:
        """
        Checks differences between two integration yaml files.

        Return:
            bool. return true if the new integration contains everything in the old integration.
        """
        old_yaml_data = get_yaml(self.old)
        new_yaml_data = get_yaml(self.new)

        self.missing_items_report = self.get_differences(old_yaml_data, new_yaml_data)

        if self.print_items():
            return False

        return True

    def get_differences(self, old_data, new_data) -> dict:
        """
            Gets the different elements between the two integration yaml data.

            Args:
                old_data: The old yaml integration data.
                new_data: The new yaml integration date.

            Return:
                A dict contains all the found different elements between the integrations.
        """

        differences_result = {}

        old_commands_data = old_data['script']['commands']
        new_commands_data = new_data['script']['commands']

        commands, arguments, outputs = self.get_different_commands(old_commands_data, new_commands_data)

        parameters = self.get_different_params(old_data['configuration'], new_data['configuration'])

        if parameters:
            differences_result['parameters'] = parameters

        if commands:
            differences_result['commands'] = commands

        if arguments:
            differences_result['arguments'] = arguments

        if outputs:
            differences_result['outputs'] = outputs

        return differences_result

    def get_different_commands(self, old_commands, new_commands) -> tuple:
        """
        Checks differences between two list of the integration commands.

        Args:
            old_commands: List of the old integration commands.
            new_commands: List of the new integration commands.

        Returns:
            Three lists. Each one is a list of the found different commands/arguments/outputs.
        """
        commands = []
        arguments = []
        outputs = []

        # for each old integration command check if exist in the new, if not, check what is missing
        for old_command in old_commands:
            if old_command not in new_commands:
                new_command = IntegrationDiffDetector.check_if_element_exist(old_command, new_commands, 'name')

                if not new_command:
                    commands.append({
                        'type': 'commands',
                        'name': old_command['name'],
                        'message': f'Missing the command \'{old_command["name"]}\'.'
                    })

                else:
                    # Gets all the fields that are different between the two commands
                    changed_fields = [field for field in new_command if field in old_command and
                                      new_command[field] != old_command[field]]

                    if 'arguments' in changed_fields:
                        arguments.extend(self.get_different_arguments(new_command, old_command))

                    if 'outputs' in changed_fields:
                        outputs.extend(self.get_different_outputs(new_command, old_command))

        return commands, arguments, outputs

    def get_different_arguments(self, new_command, old_command) -> list:
        """
        Checks for different arguments between two commands.

        Args:
            new_command: The new integration command.
            old_command: The old integration command.

        Return:
            List of all the found different arguments.
        """
        arguments = []

        new_command_arguments = new_command['arguments']
        old_command_arguments = old_command['arguments']

        for argument in old_command_arguments:
            if argument not in new_command_arguments:

                new_command_argument = IntegrationDiffDetector.check_if_element_exist(argument, new_command_arguments,
                                                                                      'name')

                if not new_command_argument:
                    arguments.append({
                        'type': 'arguments',
                        'name': argument['name'],
                        'command_name': new_command['name'],
                        'message': f'Missing the argument \'{argument["name"]}\' in command \'{new_command["name"]}\'.'
                    })

                else:
                    # Gets all the fields that are different between the two arguments
                    changed_fields = [field for field in new_command_argument if
                                      (field in argument and new_command_argument[field] != argument[field]) or
                                      (field not in argument and new_command_argument[field])]

                    arguments.extend(self.check_changed_fields(element=new_command_argument, element_type='arguments',
                                                               fields_to_check=ARGUMENT_FIELDS_TO_CHECK,
                                                               changed_fields=changed_fields,
                                                               command=new_command))

        return arguments

    @staticmethod
    def check_changed_fields(element, element_type, fields_to_check, changed_fields, command=None) -> list:
        """
        Checks for important changed fields in a given element.

        Args:
            element: The element to check.
            element_type: The element type.
            fields_to_check: List of the important fields to check if changed.
            changed_fields: List of changed fields.
            command: The command to check his argument.

        Return:
            A list contain all the elements with important changed fields.
        """
        result = []

        for field in fields_to_check:
            if field in changed_fields:

                # We want to return the element only if his field was False and changed to be True.
                if (field == 'required' or field == 'isArray') and not element[field]:
                    continue

                if element_type == 'arguments':
                    result.append({
                        'type': element_type,
                        'name': element['name'],
                        'command_name': command["name"],
                        'message': f'The argument \'{element["name"]}\' in command \'{command["name"]}\' '
                                   f'was changed in field \'{field}\'.'
                    })

                elif element_type == 'parameters':
                    result.append({
                        'type': element_type,
                        'name': element['display'],
                        'message': f'The parameter \'{element["display"]}\' was changed in field \'{field}\'.'
                    })

        return result

    @staticmethod
    def get_different_outputs(new_command, old_command) -> list:
        """
        Checks for different outputs between two commands.

        Args:
            new_command: The new integration command.
            old_command: The old integration command.

        Return:
            List of all the found different outputs.
        """
        outputs = []

        new_command_outputs = new_command['outputs']
        old_command_outputs = old_command['outputs']

        for output in old_command_outputs:
            if output not in new_command_outputs:

                new_command_output = IntegrationDiffDetector.check_if_element_exist(output, new_command_outputs,
                                                                                    'contextPath')

                if not new_command_output:
                    outputs.append({
                        'type': 'outputs',
                        'name': output['contextPath'],
                        'command_name': new_command["name"],
                        'message': f'Missing the output \'{output["contextPath"]}\' in command '
                                   f'\'{new_command["name"]}\'.'
                    })

                else:
                    # Gets all the fields that are different between the two outputs
                    changed_fields = [field for field in new_command_output if
                                      (field in output and new_command_output[field] != output[field]) or
                                      (field not in output and new_command_output[field])]

                    if 'type' in changed_fields:
                        outputs.append({
                            'type': 'outputs',
                            'name': output['contextPath'],
                            'command_name': new_command["name"],
                            'message': f'The output \'{output["contextPath"]}\' in command '
                                       f'\'{new_command["name"]}\' was changed in field \'type\'.'
                        })

        return outputs

    def get_different_params(self, old_params, new_params) -> list:
        """
        Checks differences between two list of the integration parameters.

        Args:
            old_params: The old integration parameters.
            new_params: The new integration parameters.

        Return:
            List of all the found different parameters.
        """
        parameters = []

        for old_param in old_params:
            if old_param not in new_params:
                param = self.check_if_element_exist(old_param, new_params, 'display')

                if not param:
                    parameters.append({
                        'type': 'parameters',
                        'name': old_param['display'],
                        'message': f'Missing the parameter \'{old_param["display"]}\'.'
                    })

                else:
                    # Gets all the fields that are different between the two params
                    changed_fields = [field for field in param if field in old_param and
                                      param[field] != old_param[field]]

                    parameters.extend(self.check_changed_fields(element=param, element_type='parameters',
                                                                fields_to_check=PARAM_FIELDS_TO_CHECK,
                                                                changed_fields=changed_fields))
        return parameters

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

    def print_missing_items(self):
        """
        Prints the missing elements report.
        """

        for missing_type in self.missing_items_report:
            click.secho(f"\nMissing {missing_type}:\n", fg='bright_red')

            for item in self.missing_items_report[missing_type]:
                click.secho(item['message'] + "\n", fg='bright_red')

    def print_items_in_docs_format(self):
        """
        Prints the version differences report in docs format so the user will can copy it to the README file.
        """

        old_yaml_data = get_yaml(self.old)
        new_yaml_data = get_yaml(self.new)

        # Gets the added items in the new integration
        new_items_report = self.get_differences(old_data=new_yaml_data, new_data=old_yaml_data)

        result = f'## V{self.get_new_version(new_yaml_data)} important information\n' \
                 '### New in this version:\n'

        for entity in new_items_report:
            if entity == 'outputs':
                continue

            entity_result = ''
            for new_item in new_items_report[entity]:
                if new_item['message'].startswith('Missing'):
                    entity_result += f'    - `{new_item["name"]}`\n' if entity != 'arguments' else \
                        f'    - `{new_item["name"]}` in command {new_item["command_name"]}\n'

            if entity_result:
                result += f'- Added the following {entity}:\n' + entity_result + '\n'

        result += '### Changed in this version:\n'

        for entity in self.missing_items_report:
            if entity == 'outputs':
                continue

            entity_result = ''
            for changed_item in self.missing_items_report[entity]:
                if changed_item['message'].startswith('The'):
                    entity_result += f'    - `{changed_item["name"]}`\n' if entity != 'arguments' else \
                        f'    - `{changed_item["name"]}` in command {changed_item["command_name"]}\n'

            if entity_result:
                result += f'- Changed the following {entity}:\n' + entity_result + '\n'

        result += '### Removed in this version:\n'

        for entity in self.missing_items_report:
            if entity == 'outputs':
                continue

            entity_result = ''
            for removed_item in self.missing_items_report[entity]:
                if removed_item['message'].startswith('Missing'):
                    entity_result += f'    - `{removed_item["name"]}`\n' if entity != 'arguments' else \
                        f'    - `{removed_item["name"]}` in command {removed_item["command_name"]}\n'

            if entity_result:
                result += f'- Removed the following {entity}:\n' + entity_result + '\n'

        click.secho(result)

    def print_items(self) -> bool:
        """
        Prints the different elements report.

        Return:
            bool. return true if found items to print and false if not.
        """

        if not self.missing_items_report:
            click.secho("The integrations are backwards compatible", fg='green')
            return False

        if self.docs_format_output:
            self.print_items_in_docs_format()

        else:
            self.print_missing_items()
        return True

    @staticmethod
    def get_new_version(new_yml_data):

        version = new_yml_data['display'].rsplit(' ', 1)[1]

        if version[0].lower() == 'v' and len(version) == 2:
            return version[1]
        return ''
