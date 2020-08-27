import os
import re
from typing import Tuple

from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SCHEMAS_PATH,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class BasePlaybookYMLFormat(BaseUpdateYML):
    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = False):
        super().__init__(input, output, path, from_version, no_validate)

    def add_description(self):
        """Add empty description to playbook and tasks."""
        print('Adding empty descriptions to relevant tasks')
        for task_id, task in self.data.get('tasks', {}).items():
            if not task['task'].get('description') and task['type'] in ['title', 'start', 'playbook']:
                task['task'].update({'description': ''})

    def update_fromversion_by_user(self):
        """If no fromversion is specified, asks the user for it's value and updates the playbook."""

        if not self.data.get('fromversion', ''):
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
                    self.data['fromversion'] = user_desired_version
                    is_input_version_valid = True
                else:
                    print_error('Version format is not valid')

    def run_format(self):
        self.update_fromversion_by_user()
        super().update_yml()
        self.add_description()
        self.save_yml_to_destination_file()

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the playbook YML updater."""
        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, self.initiate_file_validator(PlaybookValidator)


class PlaybookYMLFormat(BasePlaybookYMLFormat):
    """PlaybookYMLFormat class is designed to update playbooks YML file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
    """

    def delete_sourceplaybookid(self):
        """Delete the not needed sourceplaybookid fields"""
        print('Removing sourceplaybookid field from playbook')
        if 'sourceplaybookid' in self.data:
            self.data.pop('sourceplaybookid', None)

    def remove_copy_and_dev_suffixes_from_subplaybook(self):
        for task_id, task in self.data.get('tasks', {}).items():
            if task['task'].get('playbookName'):
                task['task']['playbookName'] = task['task'].get('playbookName').replace('_dev', ''). \
                    replace('_copy', '')
                task['task']['name'] = task['task'].get('name').replace('_dev', ''). \
                    replace('_copy', '')

    def update_playbook_task_name(self):
        """Updates the name of the task to be the same as playbookName it is running."""
        print('Updating name of tasks who calls other playbooks to their name')

        for task_id, task in self.data.get('tasks', {}).items():
            if task.get('type', '') == 'playbook':
                task_name = task.get('task').get('playbookName', task.get('task').get('playbookId', ''))
                if task_name:
                    task['task']['name'] = task_name

    def run_format(self) -> int:
        try:
            print_color(f'\n======= Updating file: {self.source_file} =======', LOG_COLORS.WHITE)
            self.update_tests()
            self.remove_copy_and_dev_suffixes_from_subplaybook()
            self.update_conf_json('playbook')
            self.delete_sourceplaybookid()
            self.update_playbook_task_name()
            super().run_format()
            return SUCCESS_RETURN_CODE
        except Exception:
            return ERROR_RETURN_CODE


class TestPlaybookYMLFormat(BasePlaybookYMLFormat):
    """TestPlaybookYMLFormat class is designed to update playbooks YML file according to Demisto's convention.

          Attributes:
              input (str): the path to the file we are updating at the moment.
              output (str): the desired file name to save the updated version of the YML to.
      """

    def __init__(self, *args, **kwargs):
        kwargs['path'] = os.path.normpath(
            os.path.join(__file__, "..", "..", "common", SCHEMAS_PATH, 'playbook.yml'))
        super().__init__(*args, **kwargs)

    def run_format(self) -> int:
        try:
            print_color(f'\n======= Updating file: {self.source_file} =======', LOG_COLORS.WHITE)
            super().run_format()
            return SUCCESS_RETURN_CODE
        except Exception:
            return ERROR_RETURN_CODE
