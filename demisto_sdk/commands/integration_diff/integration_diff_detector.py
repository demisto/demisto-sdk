import os

from demisto_sdk.commands.common.tools import (get_yaml, print_error,
                                               print_success)


class IntegrationDiffDetector:

    def __init__(self, new: str = '', old: str = ''):

        if not os.path.exists(new) or not os.path.exists(old):
            print_error('No such file or directory.')

        self.new = new
        self.old = old

        self.fount_missing = False
        self.missing_details_report: dict = {
            'commands': [],
            'arguments': [],
            'outputs': []
        }

    def check_diff(self):
        old_yaml_data = get_yaml(self.old)
        new_yaml_data = get_yaml(self.new)

        old_commands = old_yaml_data['script']['commands']
        new_commands = new_yaml_data['script']['commands']

        for old_command in old_commands:
            if old_command not in new_commands:
                self.check_command(old_command, new_commands)

        self.print_missing_items()
        if self.missing_details_report:
            return True
        return False

    def check_command(self, old_command, new_commands):

        new_command = {}

        for n_command in new_commands:
            if n_command['name'] == old_command['name']:
                new_command = n_command

        if not new_command:
            self.add_changed_item(item_type='commands', item_name=old_command['name'],
                                  message=f'Missing the command {old_command["name"]}.')
        else:
            changed_fields = [filed for filed in new_command if new_command[filed] != old_command[filed]]

            if 'arguments' in changed_fields:
                self.check_command_arguments(new_command, old_command)

            if 'outputs' in changed_fields:
                self.check_command_outputs(new_command, old_command)

    def check_command_arguments(self, new_command, old_command):

        new_command_arguments = new_command['arguments']
        old_command_arguments = old_command['arguments']

        for argument in old_command_arguments:
            if argument not in new_command_arguments:

                new_command_argument = {}
                for new_command_arg in new_command_arguments:

                    if new_command_arg['name'] == argument['name']:
                        new_command_argument = new_command_arg

                if not new_command_argument:
                    self.add_changed_item(item_type='arguments', item_name=argument['name'],
                                          message=f'Missing the argument {argument["name"]} in command '
                                                  f'{new_command["name"]}.', command_name=new_command['name'])

                else:
                    changed_fields = [filed for filed in new_command_argument
                                      if new_command_argument[filed] != argument[filed]]

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

        new_command_outputs = new_command['outputs']
        old_command_outputs = old_command['outputs']

        for output in old_command_outputs:
            if output not in new_command_outputs:

                new_command_output = {}
                for new_command_outp in new_command_outputs:

                    if new_command_outp['contextPath'] == output['contextPath']:
                        new_command_output = new_command_outp

                if not new_command_output:
                    self.add_changed_item(item_type='outputs', item_name=output['contextPath'],
                                          message=f'The output {output["contextPath"]} was removed from command '
                                                  f'{new_command["name"]}.', command_name=new_command['name'])

                else:
                    changed_fields = [filed for filed in new_command_output
                                      if new_command_output[filed] != output[filed]]

                    if 'type' in changed_fields:
                        self.add_changed_item(item_type='outputs', item_name=output['contextPath'],
                                              message=f'The output {output["contextPath"]} type in command '
                                                      f'{new_command["name"]} was changed.',
                                              command_name=new_command["name"])

    def add_changed_item(self, item_type, item_name, message, command_name=''):

        item = {
            'type': item_type,
            'name': item_name
        }

        if item_type != 'commands' and command_name:
            item['command_name'] = command_name

        item['message'] = message

        self.missing_details_report[item_type].append(item)
        self.fount_missing = True

    def print_missing_items(self):
        if not self.fount_missing:
            print_success("No missing was found")
            return

        for missing_type in self.missing_details_report:
            if self.missing_details_report[missing_type]:
                print_error(f"\nFount missing {missing_type}:\n")

                for item in self.missing_details_report[missing_type]:
                    print_error(item['message'] + "\n")
