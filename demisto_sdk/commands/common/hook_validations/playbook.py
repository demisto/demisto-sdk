from typing import Dict

from demisto_sdk.commands.common.tools import print_error

from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator


class PlaybookValidator(BaseValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_playbook(self, is_new_playbook=True):  # type: (bool) -> bool
        """Check whether the playbook is valid or not.

         Args:
            is_new_playbook (bool): whether the playbook is new or modified

        Returns:
            bool. Whether the playbook is valid or not
        """

        if is_new_playbook:
            new_playbook_checks = [
                self.is_valid_version(),
                self.is_id_equals_name(),
                self.is_no_rolename(),
                self.is_root_connected_to_all_tasks(),
                self.is_condition_branches_handled()
            ]
            answers = all(new_playbook_checks)
        else:
            # for new playbooks - run all playbook checks.
            # for modified playbooks - id may not be equal to name.
            modified_playbook_checks = [
                self.is_valid_version(),
                self.is_no_rolename(),
                self.is_root_connected_to_all_tasks(),
                self.is_condition_branches_handled()
            ]
            answers = all(modified_playbook_checks)

        return answers

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
            print_error("Playbook can not have a rolename.")
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
                    is_all_condition_branches_handled = is_all_condition_branches_handled and self.is_builtin_condition_task_branches_handled(
                        task)
                # ask conditional task
                elif task.get('message'):
                    is_all_condition_branches_handled = is_all_condition_branches_handled and self.is_ask_condition_branches_handled(
                        task)
                # script conditional task
                elif task.get('scriptName'):
                    is_all_condition_branches_handled = is_all_condition_branches_handled and self.is_script_condition_branches_handled(
                        task)
        return is_all_condition_branches_handled

    def is_builtin_condition_task_branches_handled(self, task):
        """Checks whether a builtin conditional task branches are handled properly

        Return:
            bool. if the task handles all condition branches correctly.
        """
        # default condition should always exist
        is_all_condition_branches_handled: bool = True
        task_condition_labels = {'#default#'}
        for condition in task.get('conditions', []):
            label = condition.get('label')
            if label:
                task_condition_labels.add(label)
        next_tasks: Dict = task.get('nexttasks', {})
        for next_task_branch, next_task_ids in next_tasks.items():
            try:
                if next_task_ids:
                    task_condition_labels.remove(next_task_branch)
            except KeyError:
                print_error(f'Playbook conditional task with id:{task.get("id")} has task with unreachable '
                            f'next task condition "{next_task_branch}". Please remove this task or add '
                            f'this condition to condition task with id:{task.get("id")}.')
                self.is_valid = is_all_condition_branches_handled = False
        # if there are task_condition_labels left then not all branches are handled
        if task_condition_labels:
            try:
                task_condition_labels.remove('#default#')
                task_condition_labels.add('else')
            except KeyError:
                pass
            print_error(f'Playbook conditional task with id:{task.get("id")} has unhandled condition: '
                        f'{",".join(map(lambda x: f"{str(x)}", task_condition_labels))}')
            self.is_valid = is_all_condition_branches_handled = False
        return is_all_condition_branches_handled

    def is_ask_condition_branches_handled(self, task):
        """Checks whether a builtin conditional task branches are handled properly

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        next_tasks: Dict = task.get('nexttasks', {})
        # if default is handled, then it means all branches are being handled
        if '#default#' in next_tasks:
            return is_all_condition_branches_handled
        unhandled_reply_options = set(task.get('message').get('replyOptions'))
        next_tasks: Dict = task.get('nexttasks', {})
        for next_task_branch, next_task_ids in next_tasks.items():
            try:
                if next_task_ids:
                    unhandled_reply_options.remove(next_task_branch)
            except KeyError:
                pass
        if unhandled_reply_options:
            print_error(f'Playbook conditional task with id:{task.get("id")} has unhandled condition: '
                        f'{",".join(map(lambda x: f"{str(x)}", unhandled_reply_options))}')
            self.is_valid = is_all_condition_branches_handled = False
        return is_all_condition_branches_handled

    def is_script_condition_branches_handled(self, task):
        """Checks whether a script conditional task branches are handled properly

        Return:
            bool. if the task handles all condition branches correctly.
        """
        is_all_condition_branches_handled: bool = True
        next_tasks: Dict = task.get('nexttasks', {})
        if '#default#' not in next_tasks:
            print_error(f'Playbook conditional task with id:{task.get("id")} has unhandled condition: else')
            self.is_valid = is_all_condition_branches_handled = False
        if 'yes' not in next_tasks:
            print_error(f'Playbook conditional task with id:{task.get("id")} has unhandled condition: yes')
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
            print_error(f'The following tasks ids have no previous tasks: {orphan_tasks}')
        return tasks_bucket.issubset(next_tasks_bucket)
