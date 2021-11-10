from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations import \
    common_playbook_validations
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import is_string_uuid


class TestPlaybookValidator(ContentEntityValidator):
    """TestPlaybookValidator is designed to validate the correctness of the file structure we enter to content repo for
    both test playbooks and scripts.
    """

    def is_valid_test_playbook(self, validate_rn: bool = False, id_set_file=None) -> bool:
        """Check whether the test playbook is valid or not.

         Args:
            validate_rn (bool):  whether we need to validate release notes or not
            id_set_file (dict): id_set.json file if exists, None otherwise

        Returns:
            bool. Whether the playbook is valid or not
        """
        test_playbooks_check = [
            self.is_valid_file(validate_rn),
            self._is_id_uuid(),
            self._is_taskid_equals_id(),
            common_playbook_validations.check_tasks_brands(
                self.current_file, id_set_file, self.file_path, self.handle_error)
        ]
        return all(test_playbooks_check)

    def is_valid_file(self, validate_rn):
        """Check whether the test playbook or script file is valid or not
        """

        return all([
            self.is_valid_fromversion(),
        ])

    def is_valid_version(self):  # type: () -> bool
        """Check whether the test playbook version is equal to DEFAULT_VERSION (see base_validator class)

        Return:
            bool. whether the version is valid or not
        """
        return self._is_valid_version()

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
