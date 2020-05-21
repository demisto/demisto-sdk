from typing import Dict

import click
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import LOG_COLORS


class PlaybookValidator(ContentEntityValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_playbook(self, is_new_playbook: bool = True, validate_rn: bool = True) -> bool:
        """Check whether the playbook is valid or not.

         Args:
            is_new_playbook (bool): whether the playbook is new or modified
            validate_rn (bool):  whether we need to validate release notes or not

        Returns:
            bool. Whether the playbook is valid or not
        """
        if 'TestPlaybooks' in self.file_path:
            click.echo(f'Skipping validation for Test Playbook {self.file_path}', color=LOG_COLORS.YELLOW)
            return True
        if is_new_playbook:
            new_playbook_checks = [
                super().is_valid_file(validate_rn),
                self.is_valid_version(),
                self.is_id_equals_name(),
                self.is_no_rolename(),
                self.is_root_connected_to_all_tasks(),
                self.is_condition_branches_handled(),
                self.are_tests_configured()
            ]
            answers = all(new_playbook_checks)
        else:
            # for new playbooks - run all playbook checks.
            # for modified playbooks - id may not be equal to name.
            modified_playbook_checks = [
                self.is_valid_version(),
                self.is_no_rolename(),
                self.is_root_connected_to_all_tasks(),
                self.is_condition_branches_handled(),
                self.are_tests_configured()
            ]
            answers = all(modified_playbook_checks)

        return answers

    def are_tests_configured(self) -> bool:
        """
        Checks if the playbook has a TestPlaybook and if the TestPlaybook is configured in conf.json
        And prints an error message accordingly
        """
        file_type = self.structure_validator.scheme_name
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
        next_tasks: Dict = task.get('nexttasks', {})
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
                next_tasks_bucket.update(next_task_ids)
        orphan_tasks = tasks_bucket.difference(next_tasks_bucket)
        if orphan_tasks:
            error_message, error_code = Errors.playbook_unconnected_tasks(orphan_tasks)
            if not self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return tasks_bucket.issubset(next_tasks_bucket)
