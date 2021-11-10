import unittest

from demisto_sdk.commands.common.hook_validations.common_playbook_validations import (
    _is_valid_brand, check_tasks_brands)


def handle_error(error_message, error_code, file_path):
    """
    handle error stub to simulate function passed
    """
    return None


class MyTestCase(unittest.TestCase):

    ASSOCIATED_PLAYBOOK = {
        "tasks": {
            "1": {
                "id": "1",
                "task": {
                    "script": "rightname|||some-command"
                }
            }
        }
    }

    NOT_ASSOCIATED_PLAYBOOK = {
        "tasks": {
            "1": {
                "id": "1",
                "task": {
                    "script": "wrongname|||some-command"
                }
            }
        }
    }

    NO_NAME_ASSOCIATED_PLAYBOOK = {
        "tasks": {
            "1": {
                "id": "1",
                "task": {
                    "script": "|||some-command"
                }
            }
        }
    }

    NO_TASKS_PLAYBOOK = {
    }

    TASK_MISSING_PLAYBOOK = {
        "tasks": {
            "1": {
                "id": "1"
            }
        }
    }

    SCRIPT_MISSING_PLAYBOOK = {
        "tasks": {
            "1": {
                "id": "1",
                "task": {
                }
            }
        }
    }

    PIPES_MISSING_PLAYBOOK = {
        "tasks": {
            "1": {
                "id": "1",
                "task": {
                    "script": "some-command"
                }
            }
        }
    }

    ID_SET = {
        "integrations": [
            {
                "rightname": {}
            },
        ]
    }

    def test_check_tasks_brands_good_brand(self):
        """
        Given
            - Playbook with a task
            - Id set file
            - some path
            - Dummy error handler
        When
            - Playbook's task has a valid brand name
        Then
            - return True
        """
        assert check_tasks_brands(self.ASSOCIATED_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_tasks_brands_no_id_set(self):
        """
        Given
            - Playbook with a task
            - some path
            - Dummy error handler
        When
            - ID set file is missing
        Then
            - returns true
        """
        assert check_tasks_brands(self.ASSOCIATED_PLAYBOOK, None, "some path", handle_error)

    def test_check_tasks_brands_no_tasks(self):
        """
        Given
            - Playbook
            - id set
            - some path
            - Dummy error handler
        When
            - Playbook has no tasks
        Then
            - return true
        """
        assert check_tasks_brands(self.NO_TASKS_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_tasks_brands_no_specific_task(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
            - Dummy error handler
        When
            - Playbook's task is missing a task entry
        Then
            - returns true
        """
        assert check_tasks_brands(self.TASK_MISSING_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_tasks_brands_no_script(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
            - Dummy error handler
        When
            - Playbook's task is missing script entry
        Then
            - returns true
        """
        assert check_tasks_brands(self.SCRIPT_MISSING_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_tasks_brands_no_pipes(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
            - Dummy error handler
        When
            - Task's script is missing ||| before the script's name
        Then
            - returns true
        """
        assert check_tasks_brands(self.PIPES_MISSING_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_tasks_brands_bad_brand(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
            - Dummy error handler
        When
            - Playbook's task has a script with an invalid brand name
        Then
            - return False
        """
        assert not check_tasks_brands(self.NOT_ASSOCIATED_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_tasks_brands_no_brand(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
            - Dummy error handler
        When
            - Playbook's task has a script with no brand name
        Then
            - return False
        """
        assert not check_tasks_brands(self.NO_NAME_ASSOCIATED_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_is_valid_brand_found_brand(self):
        """
        Given
            - brand name
            - id set
        When
            - brand_name is a valid brand
        Then
            - return True
        """
        assert _is_valid_brand("rightname", self.ID_SET)

    def test_is_valid_brand_not_found_brand(self):
        """
        Given
            - brand name
            - id set
        When
            - brand_name is not in the id set
        Then
            - return False
        """
        assert not _is_valid_brand("wrongname", self.ID_SET)

    def test_is_valid_brand_not_found_no_brand(self):
        """
        Given
            - brand name
            - id set
        When
            - brand_name is empty
        Then
            - return False
        """
        assert not _is_valid_brand("", self.ID_SET)


if __name__ == '__main__':
    unittest.main()
