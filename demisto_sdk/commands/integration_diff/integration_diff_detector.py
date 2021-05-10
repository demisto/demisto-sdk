import os

from demisto_sdk.commands.common.tools import (get_yaml, print_error,
                                               print_success)


class IntegrationDiffDetector:

    def __init__(self, new: str = '', old: str = ''):

        if not os.path.exists(new):
            print_error('No such file or directory of the new integration.')

        if not os.path.exists(old):
            print_error('No such file or directory of the old integration.')

        self.new = new
        self.old = old

        self.fount_missing = False
        self.missing_details_report: dict = {
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

        self.print_missing_items()
        if self.missing_details_report:
            return True
        return False

    def check_command(self, old_command, new_commands):
        """Checks a specific old integration command and it's arguments and outputs if exist in the new integration"""

        new_command = IntegrationDiffDetector.check_if_element_exist(old_command, new_commands, 'name')

        if not new_command:
            self.add_changed_item(item_type='commands', item_name=old_command['name'],
                                  message=f'Missing the command {old_command["name"]}.')
        else:
            # Gets all the fields that are different between the two commands
            changed_fields = [field for field in new_command if new_command[field] != old_command[field]]

            if 'arguments' in changed_fields:
                self.check_command_arguments(new_command, old_command)

            if 'outputs' in changed_fields:
                self.check_command_outputs(new_command, old_command)

    def check_command_arguments(self, new_command, old_command):
        """Checks the old integration command arguments if exists in the new integration command"""

        new_command_arguments = new_command['arguments']
        old_command_arguments = old_command['arguments']

        for argument in old_command_arguments:
            if argument not in new_command_arguments:

                new_command_argument = IntegrationDiffDetector.check_if_element_exist(argument, new_command_arguments,
                                                                                      'name')

                if not new_command_argument:
                    self.add_changed_item(item_type='arguments', item_name=argument['name'],
                                          message=f'Missing the argument {argument["name"]} in command '
                                                  f'{new_command["name"]}.', command_name=new_command['name'])
                else:
                    # Gets all the fields that are different between the two arguments
                    changed_fields = [field for field in new_command_argument
                                      if new_command_argument[field] != argument[field]]

                    if 'default' in changed_fields:
                        self.add_changed_item(item_type='arguments', item_name=new_command_argument["name"],
                                              message=f'The default of the argument {new_command_argument["name"]} in '
                                                      f'command {new_command["name"]} was changed.',
                                              command_name=new_command["name"])

                    if 'required' in changed_fields and new_command_argument['required']:
                        self.add_changed_item(item_type='arguments', item_name=new_command_argument["name"],
                                              message=f'The argument {new_command_argument["name"]} in command '
                                                      f'{new_command["name"]} changed to be mandatory.',
                                              command_name=new_command["name"])

                    if 'isArray' in changed_fields and new_command_argument['isArray']:
                        self.add_changed_item(item_type='arguments', item_name=new_command_argument["name"],
                                              message=f'The argument {new_command_argument["name"]} in command '
                                                      f'{new_command["name"]} changed to be a comma separated.',
                                              command_name=new_command["name"])

    def check_command_outputs(self, new_command, old_command):
        """Checks the old integration command outputs if exists in the new integration command"""

        new_command_outputs = new_command['outputs']
        old_command_outputs = old_command['outputs']

        for output in old_command_outputs:
            if output not in new_command_outputs:

                new_command_output = IntegrationDiffDetector.check_if_element_exist(output, new_command_outputs,
                                                                                    'contextPath')

                if not new_command_output:
                    self.add_changed_item(item_type='outputs', item_name=output['contextPath'],
                                          message=f'The output {output["contextPath"]} was removed from command '
                                                  f'{new_command["name"]}.', command_name=new_command['name'])

                else:
                    # Gets all the fields that are different between the two outputs
                    changed_fields = [field for field in new_command_output
                                      if new_command_output[field] != output[field]]

                    if 'type' in changed_fields:
                        self.add_changed_item(item_type='outputs', item_name=output['contextPath'],
                                              message=f'The output {output["contextPath"]} type in command '
                                                      f'{new_command["name"]} was changed.',
                                              command_name=new_command["name"])

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

    def print_missing_items(self):
        """Prints the missing elements report."""

        if not self.fount_missing:
            print_success("The integrations are backwards compatible")
            return

        for missing_type in self.missing_details_report:
            if self.missing_details_report[missing_type]:
                print_error(f"\nMissing {missing_type}:\n")

                for item in self.missing_details_report[missing_type]:
                    print_error(item['message'] + "\n")
