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
                self.is_condition_branches_handled_correctly()
            ]
            answers = all(new_playbook_checks)
        else:
            # for new playbooks - run all playbook checks.
            # for modified playbooks - id may not be equal to name.
            modified_playbook_checks = [
                self.is_valid_version(),
                self.is_no_rolename(),
                self.is_condition_branches_handled_correctly()
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

    def is_condition_branches_handled_correctly(self):  # type: () -> bool
        """Check whether the playbook conditional tasks has all optional branches handled

        Return:
            bool. if the Playbook handles all condition branches correctly.
        """
        tasks = self.current_file.get('tasks', {})
        if tasks:
            for task in tasks.values():
                if task.get('type') == 'condition':
                    # default condition should always exist
                    task_condition_labels = {'#default#'}
                    for condition in task.get('conditions', []):
                        label = condition.get('label')
                        if label:
                            task_condition_labels.add(label)
                    next_tasks = task.get('nexttasks', {})
                    for next_task_branch, next_task_ids in next_tasks.items():
                        try:
                            if next_task_ids:
                                task_condition_labels.remove(next_task_branch)
                        except KeyError as e:
                            print_error('Playbook has conditional task with unreachable next task: {}'.format(str(e)))
                            self.is_valid = False
                            return False
                    # if there are task_condition_labels left then not all branches are handled
                    if task_condition_labels:
                        print_error('Playbook has conditional task with unhandled branches: {}'.format(
                            str(task_condition_labels)))
                        self.is_valid = False
                        return False
        return True
