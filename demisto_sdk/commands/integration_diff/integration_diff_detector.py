import os

import click
from demisto_sdk.commands.common.constants import (ARGUMENT_FIELDS_TO_CHECK,
                                                   INTEGRATION_ARGUMENT_TYPES,
                                                   PARAM_FIELDS_TO_CHECK)
from demisto_sdk.commands.common.tools import get_yaml


class IntegrationDiffDetector:

    def __init__(self, new: str = '', old: str = '', docs_format: bool = False):

        if not os.path.exists(new):
            click.secho('No such file or directory for the new integration version.', fg='bright_red')

        if not os.path.exists(old):
            click.secho('No such file or directory for the old integration version.', fg='bright_red')

        self.new = new
        self.old = old
        self.docs_format_output = docs_format

        self.old_yaml_data = get_yaml(self.old)
        self.new_yaml_data = get_yaml(self.new)

        self.fount_missing = False
        self.missing_items_report: dict = {}

    def check_different(self) -> bool:
        """
        Checks differences between two integration yaml files.

        Return:
            bool. return true if the new integration contains everything in the old integration.
        """

        self.missing_items_report = self.get_differences()

        if self.print_items():
            return False

        return True

    def get_differences(self) -> dict:
        """
            Gets the different elements between the two integration yaml data.

            Args:
                old_data: The old yaml integration data.
                new_data: The new yaml integration date.

            Return:
                A dict contains all the found different elements between the integrations.
        """

        differences_result = {}

        old_commands_data = self.old_yaml_data['script']['commands']
        new_commands_data = self.new_yaml_data['script']['commands']

        commands, arguments, outputs = self.get_different_commands(old_commands_data, new_commands_data)

        parameters = self.get_different_params(self.old_yaml_data['configuration'], self.new_yaml_data['configuration'])

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
                new_command = self.check_if_element_exist(old_command, new_commands, 'name')

                if not new_command:
                    commands.append({
                        'type': 'commands',
                        'name': old_command['name'],
                        'message': f'Missing the command \'{old_command["name"]}\'.',
                        'description': old_command.get('description', '')
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
                        'message': f'Missing the argument \'{argument["name"]}\' in the command \'{new_command["name"]}\'.'
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

    def check_changed_fields(self, element, element_type, fields_to_check, changed_fields, command=None) -> list:
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
                        'message': f'The argument `{element["name"]}` in the command `{command["name"]}` '
                                   f'- {self.get_change_description(field, element[field])}.',
                        'changed_field': field,
                        'changed_value': element[field]
                    })

                elif element_type == 'parameters':
                    result.append({
                        'type': element_type,
                        'name': element['display'],
                        'message': f'The parameter `{element["display"]}` '
                                   f'- {self.get_change_description(field, element[field])}.',
                        'changed_field': field,
                        'changed_value': element[field]
                    })

        return result

    @staticmethod
    def get_change_description(field, value):

        if field in ['defaultValue', 'defaultvalue']:
            return f'The default value changed to \'{value}\''

        elif field == 'required':
            return 'Is Now required'

        elif field == 'isArray':
            return 'Now supports comma separated values'

        elif field == 'type':
            return f'The type changed to \'{INTEGRATION_ARGUMENT_TYPES[str(value)]}\''

        return ''

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
                        'message': f'Missing the output \'{output["contextPath"]}\' in the command '
                                   f'\'{new_command["name"]}\'.'
                    })

                else:
                    # Gets all the fields that are different between the two outputs
                    changed_fields = [field for field in new_command_output if
                                      field in output and new_command_output[field] != output[field]]

                    if 'type' in changed_fields:
                        outputs.append({
                            'type': 'outputs',
                            'name': output['contextPath'],
                            'command_name': new_command["name"],
                            'message': f'The output \'{output["contextPath"]}\' in the command '
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
                    changed_fields = [field for field in param if
                                      (field in old_param and param[field] != old_param[field]) or
                                      (field not in old_param and param[field])]

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

    def print_items_in_docs_format(self, secho_result: bool = True):
        """
        Prints the version differences report in docs format so the user will can copy it to the README file.

        Return:
            The result as a string to print.
        """

        result = ''

        if secho_result:
            result = '\n## Breaking changes from previous versions of this integration\n' \
                     'The following sections list the changes in this version.\n\n'

        if 'commands' in self.missing_items_report:
            result += '### Commands\nThe following commands were removed in this version:\n'

            for command in self.missing_items_report['commands']:
                result += f'* *{command["name"]}* - this command was replaced by XXX.\n'

        if 'outputs' in self.missing_items_report:
            result += '\n### Outputs\nThe following outputs were removed in this version:\n'

            output_per_command = self.get_elements_per_command(self.missing_items_report['outputs'])
            for command in output_per_command:
                result += f'\nCommand \'{command}\':\n'

                for output in output_per_command[command]:
                    result += f'* *{output["name"]}* - this output was replaced by XXX.\n'

        if secho_result:
            result += '\n## Additional Considerations for this Version\n* Insert any API changes, ' \
                      'any behavioral changes, limitations, or restrictions that would be new to this version.'
            click.secho(result)

        return result

    def get_items_in_docs_format(self, items_report, action_type) -> str:
        """
        Gets the differences in docs format.

        Args:
            items_report: A report of the items to print.
            action_type: The type of the difference (Added, Changed or Removed).

        Return:
            String of the items in docs format to print.
        """
        result = ''

        for entity in items_report:
            entity_result = ''
            if entity == 'outputs':
                split_outputs = self.get_elements_per_command(items_report[entity])

                entity_result += f'- There are {action_type.lower()} outputs in the commands `{", ".join(list(split_outputs))}`\n'

            else:

                if action_type == 'Changed':
                    for item in items_report[entity]:
                        # If it's not a changed item we won't want to print this here
                        if 'changed_field' not in item:
                            continue

                        entity_result += f'- {item["message"]}\n'

                else:
                    # Remove all changed items
                    items_not_changed = [item for item in items_report[entity] if "changed_field" not in item]

                    if entity == 'arguments':
                        args_per_command = self.get_elements_per_command(items_not_changed)

                        for command in args_per_command:
                            entity_result += f'- The arguments `{", ".join([arg["name"] for arg in args_per_command[command]])}` ' \
                                             f'in the command `{command}`.\n'

                    else:
                        for item in items_not_changed:
                            entity_result += f'- `{item["name"]}` - {item.get("description", "")}\n' \
                                if entity == 'commands' and action_type == 'Added' else f'- `{item["name"]}`\n'

            if entity_result:
                result += f'#### {action_type} the following {entity}:\n' + entity_result + '\n'

        return result

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
            return False

        else:
            self.print_missing_items()
        return True

    @staticmethod
    def get_elements_per_command(list_of_elements) -> dict:
        """
        Split a given list of elements by command.

        Args:
            list_of_elements: The list of elements to split.

        Return:
            Dict contains the split elements by command name.
        """

        result: dict = {}

        for element in list_of_elements:
            if element['command_name'] in result:
                result[element['command_name']].append(element)

            else:
                result[element['command_name']] = [element]

        return result
