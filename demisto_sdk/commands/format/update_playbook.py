import re

from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML
from demisto_sdk.commands.common.tools import print_color, LOG_COLORS, print_error
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator


class PlaybookYMLFormat(BaseUpdateYML):
    """PlaybookYMLFormat class is designed to update playbooks YML file according to Demisto's convention.

        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file_name (str): the desired file name to save the updated version of the YML to.
            yml_data (Dict): YML file data arranged in a Dict.
            id_and_version_location (Dict): the object in the yml_data that holds the is and version values.
    """

    def __init__(self, source_file='', output_file_name=''):
        super().__init__(source_file, output_file_name)

    def add_description(self):
        """Add empty description to playbook and tasks."""
        print(F'Adding empty descriptions to relevant tasks')
        if 'description' not in self.yml_data:
            self.yml_data['description'] = ''

        for task_id, task in self.yml_data.get('tasks', {}).items():
            if task['task'].get('description'):
                continue  # In case we already have a description we should skip the setting of an empty value

            task['task'].update({'description': ''})

    def update_playbook_task_name(self):
        """Updates the name of the task to be the same as playbookName it is running."""
        print(F'Updating name of tasks who calls other playbooks to their name')

        for task_id, task in self.yml_data.get('tasks', {}).items():
            if task.get('type', '') == 'playbook':
                task['task']['name'] = task['task']['playbookName']

    def update_fromversion(self):
        """If no fromversion is specified, asks the user for it's value and updates the playbook."""
        print(F'Updating fromversion tag')

        if not self.yml_data.get('fromversion', ''):
            print_color('No fromversion is specified for this playbook, would you like me to update for you? [Y/n]',
                        LOG_COLORS.RED)
            user_answer = input()
            if user_answer in ['n', 'N', 'no', 'No']:
                print_error('Moving forward without updating fromversion tag')
                return

            is_input_version_valid = False
            while not is_input_version_valid:
                print_color('Please specify the desired version X.X.X', LOG_COLORS.YELLOW)
                user_desired_version = input()
                if re.match(r'\d+\.\d+\.\d+', user_desired_version):
                    self.yml_data['fromversion'] = user_desired_version
                    is_input_version_valid = True
                else:
                    print_error('Version format is not valid')

    def delete_sourceplaybookid(self):
        """Delete the not needed sourceplaybookid fields"""
        print(F'Removing sourceplaybookid field from playbook')
        if 'sourceplaybookid' in self.yml_data:
            self.yml_data.pop('sourceplaybookid', None)

    def format_file(self):
        """Manager function for the playbook YML updater."""
        super().update_yml()

        print_color(F'========Starting updates for playbook: {self.source_file}=======', LOG_COLORS.YELLOW)

        self.add_description()
        self.update_playbook_task_name()
        self.update_fromversion()
        self.save_yml_to_destination_file()

        print_color(F'========Finished updates for playbook: {self.output_file_name}=======', LOG_COLORS.YELLOW)

        return self.initiate_file_validator(PlaybookValidator, 'playbook')
