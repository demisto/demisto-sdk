from typing import Dict, Union

import demisto_client
from demisto_sdk.commands.common.constants import (DEFAULT_VERSION,
                                                   FEATURE_BRANCHES,
                                                   OLDEST_SUPPORTED_VERSION,
                                                   PLAYBOOK, FileType)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.yaml_content_object import \
    YAMLContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from packaging.version import Version
from pipenv.patched.piptools import click
from wcmatch.pathlib import Path


class Playbook(YAMLContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, PLAYBOOK)
        self.base = base if base else BaseValidator()

    def upload(self, client: demisto_client):
        """
        Upload the playbook to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_playbook(file=self.path)

    def validate(self):
        if self.base.file_type == FileType.TEST_PLAYBOOK:
            return self.is_valid_test_playbook()

        if self.check_if_integration_is_deprecated():
            click.echo(f"Validating deprecated file: {self.path}")
            return self.is_valid_as_deprecated()

        return self.is_valid_playbook()

    def is_valid_test_playbook(self):
        return all([
            self.is_valid_fromversion(),
            self.is_valid_version()
        ])

    def is_valid_playbook(self) -> bool:
        """Check whether the playbook is valid or not.

        Returns:
            bool. Whether the playbook is valid or not
        """
        if 'TestPlaybooks' in str(self.path):
            click.secho(f'Skipping validation for Test Playbook {self.path}', fg='yellow')
            return True
        if not self.base.is_modified:
            new_playbook_checks = [
                self.is_valid_fromversion(),
                self.is_valid_version(),
                self.is_id_equals_name(),
                self.is_no_rolename(),
                self.is_root_connected_to_all_tasks(),
                self.is_using_instance(),
                self.is_condition_branches_handled(),
                self.is_delete_context_all_in_playbook(),
                self.are_tests_configured(),
                self.is_valid_as_deprecated(),
                self.is_script_id_valid(),
            ]
            answers = all(new_playbook_checks)
        else:
            # for new playbooks - run all playbook checks.
            # for modified playbooks - id may not be equal to name.
            modified_playbook_checks = [
                self.is_valid_fromversion(),
                self.is_valid_version(),
                self.is_no_rolename(),
                self.is_root_connected_to_all_tasks(),
                self.is_using_instance(),
                self.is_condition_branches_handled(),
                self.is_delete_context_all_in_playbook(),
                self.are_tests_configured(),
                self.is_script_id_valid(),
            ]
            answers = all(modified_playbook_checks)

        return answers

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(self.path)):
                return False
        return True

    def is_id_equals_name(self):
        """Validate that the id of the file equals to the name.

        Returns:
            bool. Whether the file's id is equal to to its name
        """

        file_id = self.get('id', '')
        name = self.get('name', '')
        if file_id != name:
            error_message, error_code = Errors.id_should_equal_name(name, file_id)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(self.path)):
                return False

        return True

    def is_no_rolename(self):  # type: () -> bool
        """Check whether the playbook has a rolename

        Return:
            bool. if the Playbook has a rolename it is not valid.
        """
        rolename = self.get('rolename', None)
        if rolename:
            error_message, error_code = Errors.playbook_cant_have_rolename()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def is_root_connected_to_all_tasks(self):  # type: () -> bool
        """Check whether the playbook root is connected to all tasks

        Return:
            bool. if the Playbook has root is connected to all tasks.
        """
        start_task_id = self.get('starttaskid')
        tasks = self.get('tasks', {})
        tasks_bucket = set()
        next_tasks_bucket = set()
        for task_id, task in tasks.items():
            if task_id != start_task_id:
                tasks_bucket.add(task_id)
            next_tasks = task.get('nexttasks', {})
            for next_task_ids in next_tasks.values():
                if next_task_ids:
                    next_tasks_bucket.update(next_task_ids)
        orphan_tasks = tasks_bucket.difference(next_tasks_bucket)
        if orphan_tasks:
            error_message, error_code = Errors.playbook_unconnected_tasks(orphan_tasks)
            if not self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return tasks_bucket.issubset(next_tasks_bucket)

    def is_using_instance(self) -> bool:
        """
        Check if there is an existing task that uses specific instance.
        Returns:
            True if using specific instance exists else False.
        """
        tasks: Dict = self.get('tasks', {})
        for task in tasks.values():
            scriptargs = task.get('scriptarguments', {})
            if scriptargs and scriptargs.get('using', {}):
                error_message, error_code = Errors.using_instance_in_playbook()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False
        return True

    def is_builtin_condition_task_branches_handled(self, task: Dict) -> bool:
        """Checks whether a builtin conditional task branches are handled properly
        NOTE: The function uses str.upper() on branches to be case insensitive

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        # ADD all possible conditions to task_condition_labels (UPPER)
        # #default# condition should always exist in a builtin condition
        task_condition_labels = set()
        for condition in task.get('conditions', []):
            label = condition.get('label')
            if label:
                # Need to cast it to string because otherwise it's parsed as boolean
                task_condition_labels.add(str(label).upper())

        # REMOVE all used condition branches from task_condition_labels (UPPER)
        next_tasks: Dict = task.get('nexttasks', {})
        for next_task_branch in next_tasks.keys():
            try:
                if next_task_branch:
                    # Need to cast it to string because otherwise it's parsed as boolean
                    task_condition_labels.remove(str(next_task_branch).upper())
            except KeyError as e:
                # else doesn't have a path, skip error
                if '#DEFAULT#' == e.args[0]:
                    continue
                error_message, error_code = Errors.playbook_unreachable_condition(task.get('id'), next_task_branch)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_all_condition_branches_handled = False

        # if there are task_condition_labels left then not all branches are handled
        if task_condition_labels:
            error_message, error_code = Errors.playbook_unhandled_condition(task.get('id'), task_condition_labels)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_all_condition_branches_handled = False

        return is_all_condition_branches_handled

    def is_ask_condition_branches_handled(self, task: Dict) -> bool:
        """Checks whether a builtin conditional task branches are handled properly
        NOTE: The function uses str.upper() on branches to be case insensitive

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        next_tasks: Dict = task.get('nexttasks', {})
        # if default is handled, then it means all branches are being handled
        if '#default#' in next_tasks:
            return is_all_condition_branches_handled

        # ADD all replyOptions to unhandled_reply_options (UPPER)
        unhandled_reply_options = set(map(str.upper, task.get('message', {}).get('replyOptions', [])))

        # Remove all nexttasks from unhandled_reply_options (UPPER)
        for next_task_branch, next_task_id in next_tasks.items():
            try:
                if next_task_id:
                    unhandled_reply_options.remove(next_task_branch.upper())
            except KeyError:
                error_message, error_code = Errors.playbook_unreachable_condition(task.get('id'), next_task_branch)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_all_condition_branches_handled = False

        if unhandled_reply_options:
            error_message, error_code = Errors.playbook_unhandled_condition(task.get('id'), unhandled_reply_options)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_all_condition_branches_handled = False
        return is_all_condition_branches_handled

    def is_script_condition_branches_handled(self, task: Dict) -> bool:
        """Checks whether a script conditional task branches are handled properly

        Args:
            task (dict): task json loaded from a yaml

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        next_tasks: Dict = task.get('nexttasks', {})
        if '#default#' not in next_tasks:
            error_message, error_code = Errors.playbook_unhandled_condition(task.get('id'), {'else'})
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_all_condition_branches_handled = False

        if len(next_tasks) < 2:
            # there should be at least 2 next tasks, we don't know what condition is missing, but we know it's missing
            error_message, error_code = Errors.playbook_unhandled_condition(task.get('id'), {})
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_all_condition_branches_handled = False

        return is_all_condition_branches_handled

    def is_condition_branches_handled(self):  # type: () -> bool
        """Check whether the playbook conditional tasks has all optional branches handled

        Return:
            bool. if the Playbook handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        tasks: Dict = self.get('tasks', {})
        for task in tasks.values():
            if task.get('type') == 'condition':
                # builtin conditional task
                if task.get('conditions'):
                    is_all_condition_branches_handled = self.is_builtin_condition_task_branches_handled(
                        task) and is_all_condition_branches_handled
                # ask conditional task
                elif task.get('message'):
                    is_all_condition_branches_handled = self.is_ask_condition_branches_handled(
                        task) and is_all_condition_branches_handled
                # script conditional task
                elif task.get('scriptName'):
                    is_all_condition_branches_handled = self.is_script_condition_branches_handled(
                        task) and is_all_condition_branches_handled
        return is_all_condition_branches_handled

    def is_delete_context_all_in_playbook(self) -> bool:
        """
        Check if delete context all=yes exist in playbook.
        Returns:
            True if delete context exists else False.
        """
        tasks: Dict = self.get('tasks', {})
        for task in tasks.values():
            curr_task = task.get('task', {})
            scriptargs = task.get('scriptarguments', {})
            if curr_task and scriptargs and curr_task.get('scriptName', '') == 'DeleteContext' \
                    and scriptargs.get('all', {}).get('simple', '') == 'yes':
                error_message, error_code = Errors.playbook_cant_have_deletecontext_all()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return False
        return True

    def are_tests_configured(self) -> bool:
        """
        Checks if the playbook has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        file_type = self.base.file_type.value

        if not self.get('tests'):
            error_message, error_code = Errors.no_test_playbook(self.path, file_type)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True

    def check_if_integration_is_deprecated(self):
        is_deprecated = self.get('hidden', False)

        toversion_is_old = self.to_version < Version(OLDEST_SUPPORTED_VERSION)

        return is_deprecated or toversion_is_old

    def is_valid_as_deprecated(self) -> bool:
        is_valid = True
        is_hidden = self.get('hidden', False)
        description = self.get('description', '')
        if is_hidden:
            if not description.startswith('Deprecated.'):
                error_message, error_code = Errors.invalid_deprecated_playbook()
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    is_valid = False
        return is_valid

    def check_script_id(self, script_id_used_in_task, id_set_scripts):
        """
        Checks if script id exists in at least one of id_set's dicts
        Args:
            script_id_used_in_task (str):  script id from playbook
            id_set_scripts (list): all scripts of id_set
        Returns:
            True if script_used_in_task exists in id_set
        """
        return any([script_id_used_in_task in id_set_dict for id_set_dict in id_set_scripts])

    def check_script_name(self, pb_script_name, id_set_scripts):
        """
        Checks if script name exists in at least one of id_set's dicts as value of the key 'name'
        Args:
            pb_script_name (str):  script name from playbook
            id_set_scripts (list): all scripts of id_set
        Returns:
            True if pb_script_name exists in id_set
        """
        return any(
            [pb_script_name == id_set_dict[key].get('name') for id_set_dict in id_set_scripts
             for key in id_set_dict])

    def is_script_id_valid(self):
        """Checks whether a script id is valid (i.e id exists in set_id)

        Return:
            bool. if all scripts ids of this playbook are valid.
        """
        is_valid = True

        if not self.base.id_set_file:
            click.secho("Skipping playbook script id validation. Could not read id_set.json.", fg="yellow")
            return is_valid

        id_set_scripts = self.base.id_set_file.get("scripts")
        pb_tasks = self.get('tasks', {})
        for _, task_dict in pb_tasks.items():
            pb_task = task_dict.get('task', {})
            script_id_used_in_task = pb_task.get('script')
            task_script_name = pb_task.get('scriptName')
            script_entry_to_check = script_id_used_in_task if script_id_used_in_task else task_script_name  # i.e
            # script id or script name
            integration_script_flag = "|||"  # skipping all builtin integration scripts

            is_script_id_should_be_checked = script_id_used_in_task \
                and integration_script_flag not in script_id_used_in_task
            if is_script_id_should_be_checked:
                is_valid = self.check_script_id(script_id_used_in_task, id_set_scripts)
            elif task_script_name and integration_script_flag not in task_script_name:
                is_valid = self.check_script_name(task_script_name, id_set_scripts)

            if not is_valid:
                error_message, error_code = Errors.invalid_script_id(script_entry_to_check, pb_task)
                if self.base.handle_error(error_message, error_code, file_path=self.path):
                    return is_valid
        return is_valid

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.base.prev_ver or feature_branch_name in self.base.branch_name)
               for feature_branch_name in FEATURE_BRANCHES):
            return False

        return True

    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromversion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True
