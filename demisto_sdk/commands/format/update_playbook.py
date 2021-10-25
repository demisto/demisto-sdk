import os
import re
import uuid
from distutils.version import LooseVersion
from typing import Tuple

import click
from git import InvalidGitRepositoryError

from demisto_sdk.commands.common.constants import PLAYBOOK, FileType
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.tools import (find_type, get_yaml,
                                               is_string_uuid, write_yml)
from demisto_sdk.commands.format.format_constants import (ERROR_RETURN_CODE,
                                                          SCHEMAS_PATH,
                                                          SKIP_RETURN_CODE,
                                                          SUCCESS_RETURN_CODE,
                                                          VERSION_6_0_0)
from demisto_sdk.commands.format.update_generic_yml import BaseUpdateYML


class BasePlaybookYMLFormat(BaseUpdateYML):
    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 assume_yes: bool = False,
                 deprecate: bool = False,
                 add_tests: bool = False):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
                         verbose=verbose, assume_yes=assume_yes, deprecate=deprecate, add_tests=add_tests)

    def add_description(self):
        """Add empty description to playbook and tasks."""
        if self.verbose:
            click.echo('Adding descriptions for the playbook and to relevant tasks')
        if 'description' not in set(self.data.keys()):
            click.secho('No description is specified for this playbook, would you like to add a description? [Y/n]',
                        fg='bright_red')
            user_answer = ''
            while not user_answer:
                user_answer = input()
                if user_answer in ['n', 'N', 'no', 'No']:
                    user_description = ''
                    self.data['description'] = user_description
                elif user_answer in ['y', 'Y', 'yes', 'Yes']:
                    user_description = input("Please enter the description\n")
                    self.data['description'] = user_description
                else:
                    click.secho('Invalid input, would you like to add a description? [Y/n]', fg='bright_red')
                    user_answer = ''

        for task_id, task in self.data.get('tasks', {}).items():
            if not task['task'].get('description') and task['type'] in ['title', 'start', 'playbook']:
                task['task'].update({'description': ''})

    def update_fromversion_by_user(self):
        """If no fromversion is specified, asks the user for it's value and updates the playbook."""

        if not self.data.get('fromversion', ''):

            if self.assume_yes:
                if self.verbose:
                    if self.from_version:
                        click.echo(f"Adding `fromversion: {self.from_version}`")

                    else:
                        click.echo(f"Adding `fromversion: {VERSION_6_0_0}`")
                self.data[
                    'fromversion'] = self.from_version if self.from_version else VERSION_6_0_0
                return

            click.secho('No fromversion is specified for this playbook, would you like me to update for you? [Y/n]',
                        fg='red')
            user_answer = input()
            if user_answer in ['n', 'N', 'no', 'No']:
                click.secho('Moving forward without updating fromversion tag', fg='yellow')
                return

            if self.from_version:
                if self.verbose:
                    click.echo(f"Adding `fromversion: {self.from_version}`")
                self.data['fromversion'] = self.from_version
                return

            is_input_version_valid = False
            while not is_input_version_valid:
                click.secho('Please specify the desired version X.X.X', fg='yellow')
                user_desired_version = input()
                if re.match(r'\d+\.\d+\.\d+', user_desired_version):
                    self.data['fromversion'] = user_desired_version
                    is_input_version_valid = True
                else:
                    click.secho('Version format is not valid', fg='red')

        elif not self.old_file and LooseVersion(self.data.get('fromversion', '0.0.0')) < \
                LooseVersion(VERSION_6_0_0):
            if self.assume_yes:
                self.data['fromversion'] = VERSION_6_0_0
            else:
                set_from_version = str(
                    input(f"\nYour current fromversion is: '{self.data.get('fromversion')}'. Do you want "
                          f"to set it to '6.0.0'? Y/N ")).lower()
                if set_from_version in ['y', 'yes']:
                    self.data['fromversion'] = VERSION_6_0_0

    def update_task_uuid(self):
        """If taskid field and the id under the task field are not from uuid type, generate uuid instead"""
        for task_key, task in self.data.get('tasks', {}).items():
            taskid = str(task.get('taskid', ''))
            task_id_under_task = str(task.get('task', {}).get('id', ''))
            if not is_string_uuid(taskid) or not is_string_uuid(task_id_under_task):
                if self.verbose:
                    click.secho(f"Taskid field and the id under task field must be from uuid format. Generating uuid "
                                f"for those fields under task key: {task_key}", fg='white')
                generated_uuid = str(uuid.uuid4())
                task['taskid'] = generated_uuid
                task['task']['id'] = generated_uuid

    def run_format(self) -> int:
        self.update_fromversion_by_user()
        super().update_yml(file_type=PLAYBOOK)
        self.add_description()
        self.update_task_uuid()
        self.save_yml_to_destination_file()
        return SUCCESS_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the playbook YML updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()


class PlaybookYMLFormat(BasePlaybookYMLFormat):
    """PlaybookYMLFormat class is designed to update playbooks YML file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
    """

    def delete_sourceplaybookid(self):
        """Delete the not needed sourceplaybookid fields"""
        if self.verbose:
            click.echo('Removing sourceplaybookid field from playbook')
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
        if self.verbose:
            click.echo('Updating name of tasks who calls other playbooks to their name')

        for task_id, task in self.data.get('tasks', {}).items():
            if task.get('type', '') == 'playbook':
                task_name = task.get('task').get('playbookName', task.get('task').get('playbookId', ''))
                if task_name:
                    task['task']['name'] = task_name

    def check_for_subplaybook_usages(self, file_path: str, current_playbook_id: str, new_playbook_id: str) -> None:
        """Check if the current_playbook_id appears in the file's playbook type tasks and change it if needed.

            Arguments:
                file_path (str): The file path to check.
                current_playbook_id (str): The current playbook ID.
                new_playbook_id (str): The new playbook ID.
        """
        updated_tasks = []
        # if the changed file is a playbook get it's data
        if find_type(file_path) in [FileType.PLAYBOOK, FileType.TEST_PLAYBOOK]:
            playbook_data = get_yaml(file_path)
            # go through all the tasks
            for task_id, task_data in playbook_data.get('tasks').items():
                # if a task is of playbook type
                if task_data.get('type') == 'playbook':
                    id_key = 'playbookId' if 'playbookId' in task_data.get('task') else 'playbookName'
                    # make sure the playbookId or playbookName use the new id and not the old
                    if task_data.get('task', {}).get(id_key) == current_playbook_id:
                        playbook_data['tasks'][task_id]['task'][id_key] = new_playbook_id
                        updated_tasks.append(task_id)

            # if any tasks were changed re-write the playbook
            if updated_tasks:
                if self.verbose:
                    click.echo(f'Found usage of playbook in {file_path} tasks: '
                               f'{" ".join(updated_tasks)} - Updating playbookId')
                write_yml(file_path, playbook_data)

    def update_playbook_usages(self) -> None:
        """Check if the current playbook is used as a sub-playbook in other changed playbooks.
        Change the playbook's id in the tasks id needed.
        """
        current_playbook_id = str(self.data.get('id'))
        new_playbook_id = str(self.data.get('name'))

        # if the id and name are the same - there is no need for this format.
        if current_playbook_id == new_playbook_id:
            return

        # gather all the changed files - if the formatted playbook was
        # modified then any additional playbook changes were changed alongside it -
        # we would use git to gather all other changed playbooks
        try:
            git_util = GitUtil()
            modified_files = git_util.modified_files(include_untracked=True)
            added_files = git_util.added_files(include_untracked=True)
            renamed_files = git_util.renamed_files(include_untracked=True, get_only_current_file_names=True)

            all_changed_files = modified_files.union(added_files).union(renamed_files)  # type: ignore[arg-type]

        except (InvalidGitRepositoryError, TypeError) as e:
            click.secho('Unable to connect to git - skipping sub-playbook checks', fg='yellow')
            if self.verbose:
                click.secho(f'The error: {e}')
            return

        for file_path in all_changed_files:
            self.check_for_subplaybook_usages(str(file_path), current_playbook_id, new_playbook_id)

    def remove_empty_fields_from_scripts(self):
        """Removes unnecessary empty fields from SetIncident, SetIndicator, CreateNewIncident, CreateNewIndicator
        scripts """

        scripts = ["setIncident", "setIndicator", "createNewIncident", "createNewIndicator"]
        for task_id, task in self.data.get('tasks', {}).items():
            current_task_script = task.get('task', {}).get('script', '')
            if any(script in current_task_script for script in scripts):
                script_args = task.get('scriptarguments', {})
                for key in list(script_args):
                    if not script_args[key]:  # if value is empty
                        script_args.pop(key)

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            self.update_playbook_usages()
            self.update_tests()
            self.remove_copy_and_dev_suffixes_from_subplaybook()
            self.update_conf_json('playbook')
            self.delete_sourceplaybookid()
            self.update_playbook_task_name()
            self.remove_empty_fields_from_scripts()
            super().run_format()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
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
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            return super().run_format()
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE
