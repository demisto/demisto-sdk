import re
from typing import Dict

import click
from demisto_sdk.commands.common.constants import DEPRECATED_REGEXES
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import LOG_COLORS, is_string_uuid


class PlaybookValidator(ContentEntityValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_playbook(self, validate_rn: bool = True, id_set_file=None) -> bool:
        """Check whether the playbook is valid or not.

         Args:
            this will also determine whether a new id_set can be created by validate.
            validate_rn (bool):  whether we need to validate release notes or not
            id_set_file (dict): id_set.json file if exists, None otherwise

        Returns:
            bool. Whether the playbook is valid or not
        """
        if 'TestPlaybooks' in self.file_path:
            click.echo(f'Skipping validation for Test Playbook {self.file_path}', color=LOG_COLORS.YELLOW)
            return True
        playbook_checks = [
            super().is_valid_file(validate_rn),
            self.is_valid_version(),
            self.is_id_equals_name(),
            self.is_no_rolename(),
            self.is_root_connected_to_all_tasks(),
            self.is_using_instance(),
            self.is_condition_branches_handled(),
            self.is_delete_context_all_in_playbook(),
            self.are_tests_configured(),
            self.is_script_id_valid(id_set_file),
            self._is_id_uuid(),
            self._is_taskid_equals_id(),
            self.verify_condition_tasks_has_else_path(),

        ]
        answers = all(playbook_checks)

        return answers

    def are_tests_configured(self) -> bool:
        """
        Checks if the playbook has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        file_type = self.structure_validator.scheme_name
        if not isinstance(file_type, str):
            file_type = file_type.value  # type: ignore

        tests = self.current_file.get('tests', [])
        return self.yml_has_test_key(tests, file_type)

    def is_id_equals_name(self):  # type: () -> bool
        """Check whether the playbook ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super(PlaybookValidator, self)._is_id_equals_name('playbook')

    def is_valid_version(self):  # type: () -> bool
        """Check whether the playbook version is equal to DEFAULT_VERSION (see base_validator class)

        Return:
            bool. whether the version is valid or not
        """
        return self._is_valid_version()

    def is_no_rolename(self):  # type: () -> bool
        """Check whether the playbook has a rolename

        Return:
            bool. if the Playbook has a rolename it is not valid.
        """
        rolename = self.current_file.get('rolename', None)
        if rolename:
            error_message, error_code = Errors.playbook_cant_have_rolename()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def is_condition_branches_handled(self):  # type: () -> bool
        """Check whether the playbook conditional tasks has all optional branches handled

        Return:
            bool. if the Playbook handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        tasks: Dict = self.current_file.get('tasks', {})
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
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = is_all_condition_branches_handled = False

        # if there are task_condition_labels left then not all branches are handled
        if task_condition_labels:
            error_message, error_code = Errors.playbook_unhandled_condition(task.get('id'), task_condition_labels)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_all_condition_branches_handled = False

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
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = is_all_condition_branches_handled = False

        if unhandled_reply_options:
            error_message, error_code = Errors.playbook_unhandled_condition(task.get('id'), unhandled_reply_options)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_all_condition_branches_handled = False
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
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_all_condition_branches_handled = False

        if len(next_tasks) < 2:
            # there should be at least 2 next tasks, we don't know what condition is missing, but we know it's missing
            error_message, error_code = Errors.playbook_unhandled_condition(task.get('id'), {})
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = is_all_condition_branches_handled = False

        return is_all_condition_branches_handled

    def is_root_connected_to_all_tasks(self):  # type: () -> bool
        """Check whether the playbook root is connected to all tasks

        Return:
            bool. if the Playbook has root is connected to all tasks.
        """
        start_task_id = self.current_file.get('starttaskid')
        tasks = self.current_file.get('tasks', {})
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
            if not self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return tasks_bucket.issubset(next_tasks_bucket)

    def is_valid_as_deprecated(self) -> bool:
        is_valid = True
        is_deprecated = self.current_file.get('deprecated', False)
        description = self.current_file.get('description', '')
        deprecated_v2_regex = DEPRECATED_REGEXES[0]
        deprecated_no_replace_regex = DEPRECATED_REGEXES[1]
        if is_deprecated:
            if re.search(deprecated_v2_regex, description) or re.search(deprecated_no_replace_regex, description):
                pass
            else:
                error_message, error_code = Errors.invalid_deprecated_playbook()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    is_valid = False
        return is_valid

    def is_delete_context_all_in_playbook(self) -> bool:
        """
        Check if delete context all=yes exist in playbook.
        Returns:
            True if delete context exists else False.
        """
        tasks: Dict = self.current_file.get('tasks', {})
        for task in tasks.values():
            curr_task = task.get('task', {})
            scriptargs = task.get('scriptarguments', {})
            if curr_task and scriptargs and curr_task.get('scriptName', '') == 'DeleteContext' \
                    and scriptargs.get('all', {}).get('simple', '') == 'yes':
                error_message, error_code = Errors.playbook_cant_have_deletecontext_all()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = False
                    return False
        return True

    def is_using_instance(self) -> bool:
        """
        Check if there is an existing task that uses specific instance.
        Returns:
            True if using specific instance exists else False.
        """
        tasks: Dict = self.current_file.get('tasks', {})
        for task in tasks.values():
            scriptargs = task.get('scriptarguments', {})
            if scriptargs and scriptargs.get('using', {}):
                error_message, error_code = Errors.using_instance_in_playbook()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self.is_valid = False
                    return False
        return True

    def is_script_id_valid(self, id_set_file):
        """Checks whether a script id is valid (i.e id exists in set_id)
        Args:
            id_set_file (dict): id_set.json file
            this will also determine whether a new id_set can be created by validate.

        Return:
            bool. if all scripts ids of this playbook are valid.
        """
        is_valid = True

        if not id_set_file:
            click.secho("Skipping playbook script id validation. Could not read id_set.json.", fg="yellow")
            return is_valid

        id_set_scripts = id_set_file.get("scripts")
        pb_tasks = self.current_file.get('tasks', {})
        for id, task_dict in pb_tasks.items():
            pb_task = task_dict.get('task', {})
            script_id_used_in_task = pb_task.get('script')
            task_script_name = pb_task.get('scriptName')
            script_entry_to_check = script_id_used_in_task if script_id_used_in_task else task_script_name  # i.e
            # script id or script name
            integration_script_flag = "|||"  # skipping all builtin integration scripts

            is_script_id_should_be_checked = script_id_used_in_task and integration_script_flag not in script_id_used_in_task
            if is_script_id_should_be_checked:
                is_valid = self.check_script_id(script_id_used_in_task, id_set_scripts)
            elif task_script_name and integration_script_flag not in task_script_name:
                is_valid = self.check_script_name(task_script_name, id_set_scripts)

            if not is_valid:
                error_message, error_code = Errors.invalid_script_id(script_entry_to_check, pb_task)
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return is_valid
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

    def _is_else_path_in_condition_task(self, task):
        next_tasks: Dict = task.get('nexttasks', {})
        return '#default#' in next_tasks

    def verify_condition_tasks_has_else_path(self):  # type: () -> bool
        """Check whether the playbook conditional tasks has else path

        Return:
            bool. if the Playbook has else path to all condition task
        """
        all_conditions_has_else_path: bool = True
        tasks: Dict = self.current_file.get('tasks', {})
        error_tasks_ids = []
        for task in tasks.values():
            if task.get('type') == 'condition':
                if not self._is_else_path_in_condition_task(task):
                    error_tasks_ids.append(task.get('id'))

        if error_tasks_ids:
            error_message, error_code = Errors.playbook_condition_has_no_else_path(error_tasks_ids)
            if self.handle_error(error_message, error_code, file_path=self.file_path, warning=True):
                all_conditions_has_else_path = False

        return all_conditions_has_else_path

    def _is_id_uuid(self):
        """
        Check that the taskid field and the id field under the task field are both on from uuid format
        Returns: True if the ids are uuid
        """
        is_valid = True
        tasks: dict = self.current_file.get('tasks', {})
        for task_key, task in tasks.items():
            taskid = str(task.get('taskid', ''))
            inner_id = str(task.get('task', {}).get('id', ''))
            is_valid_task = is_string_uuid(taskid) and is_string_uuid(inner_id)

            if not is_valid_task:
                is_valid = is_valid_task
                error_message, error_code = Errors.invalid_uuid(task_key, taskid, inner_id)
                self.handle_error(error_message, error_code, file_path=self.file_path)  # Does not break after one
                # invalid task in order to raise error for all the invalid tasks at the file

        return is_valid

    def _is_taskid_equals_id(self):
        """
        Check that taskid field and id field under task field contains equal values
        Returns: True if the values are equal

        """
        is_valid = True
        tasks: dict = self.current_file.get('tasks', {})
        for task_key, task in tasks.items():
            taskid = task.get('taskid', '')
            inner_id = task.get('task', {}).get('id', '')
            is_valid_task = (taskid == inner_id)

            if not is_valid_task:
                is_valid = is_valid_task
                error_message, error_code = Errors.taskid_different_from_id(task_key, taskid, inner_id)
                self.handle_error(error_message, error_code, file_path=self.file_path)  # Does not break after one
                # invalid task in order to raise error for all the invalid tasks at the file

        return is_valid
