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
                self.is_root_connected_to_all_tasks()
            ]
            answers = all(new_playbook_checks)
        else:
            # for new playbooks - run all playbook checks.
            # for modified playbooks - id may not be equal to name.
            modified_playbook_checks = [
                self.is_valid_version(),
                self.is_no_rolename(),
                self.is_root_connected_to_all_tasks()
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
