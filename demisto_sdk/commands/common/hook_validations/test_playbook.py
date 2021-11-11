from typing import Optional

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import is_string_uuid
import click


def _is_valid_brand(brand_name: str, id_set_file: dict) -> bool:
    """
    Goes over the id_set_file and searches for the given brand_name
    Args:
        brand_name: name of the brand
        id_set_file: dict containing all entities information
    Returns:
        True if the brand_name exists in id_set_file, False otherwise
    """
    for integration_data in id_set_file['integrations']:
        if brand_name in integration_data:
            return True
    return False


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
            self.check_tasks_brands(id_set_file)
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

    def check_tasks_brands(self, id_set_file: Optional[dict]) -> bool:
        """
        Checks that all the tasks' in a playbook which have a script also a have a valid brand name,
        Args:
            id_set_file: id set file
        Returns:
            True if all tasks who have a brand use a valid brand, False otherwise
        """
        is_valid = True

        if not id_set_file:
            click.secho("Skipping playbook brand name validation. Could not read id_set.json.", fg="yellow")
            return is_valid

        tasks: dict = self.current_file.get('tasks', {})
        for task_key, task in tasks.items():
            task_script = task.get('task', {}).get('script', None)
            if task_script is not None and '|||' in task_script:
                brand_name = task_script[:task_script.find('|||')]
                if not _is_valid_brand(brand_name, id_set_file):
                    is_valid = False
                    error_message, error_code = Errors.missing_brand_name_in_script(task_key, task_script)
                    self.handle_error(error_message, error_code, file_path=self.file_path)
        return is_valid
