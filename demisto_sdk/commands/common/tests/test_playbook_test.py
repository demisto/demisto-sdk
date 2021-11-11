import unittest
from typing import Optional

from mock import patch

from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.hook_validations.test_playbook import (
    TestPlaybookValidator, _is_valid_brand)


def mock_structure(file_path=None, current_file=None, old_file=None):
    # type: (Optional[str], Optional[dict], Optional[dict]) -> StructureValidator
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'playbook'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        structure.prev_ver = 'master'
        structure.branch_name = ''
        return structure


class TestTestPlaybookValidator:
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
        When
            - Playbook's task has a valid brand name
        Then
            - return True
        """
        structure = mock_structure("some_path", self.ASSOCIATED_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert validator.check_tasks_brands(self.ID_SET)

    def test_check_tasks_brands_no_id_set(self):
        """
        Given
            - Playbook with a task
            - some path
        When
            - ID set file is missing
        Then
            - returns true
        """
        structure = mock_structure("some_path", self.ASSOCIATED_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert validator.check_tasks_brands(None)

    def test_check_tasks_brands_no_tasks(self):
        """
        Given
            - Playbook
            - id set
            - some path
        When
            - Playbook has no tasks
        Then
            - return true
        """
        structure = mock_structure("some_path", self.NO_TASKS_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert validator.check_tasks_brands(self.ID_SET)

    def test_check_tasks_brands_no_specific_task(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
        When
            - Playbook's task is missing a task entry
        Then
            - returns true
        """
        structure = mock_structure("some_path", self.TASK_MISSING_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert validator.check_tasks_brands(self.ID_SET)

    def test_check_tasks_brands_no_script(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
        When
            - Playbook's task is missing script entry
        Then
            - returns true
        """
        structure = mock_structure("some_path", self.SCRIPT_MISSING_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert validator.check_tasks_brands(self.ID_SET)

    def test_check_tasks_brands_no_pipes(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
        When
            - Task's script is missing ||| before the script's name
        Then
            - returns true
        """
        structure = mock_structure("some_path", self.PIPES_MISSING_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert validator.check_tasks_brands(self.ID_SET)

    def test_check_tasks_brands_bad_brand(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
        When
            - Playbook's task has a script with an invalid brand name
        Then
            - return False
        """
        structure = mock_structure("some_path", self.NOT_ASSOCIATED_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert not validator.check_tasks_brands(self.ID_SET)

    def test_check_tasks_brands_no_brand(self):
        """
        Given
            - Playbook with a task
            - id set
            - some path
        When
            - Playbook's task has a script with no brand name
        Then
            - return False
        """
        structure = mock_structure("some_path", self.NO_NAME_ASSOCIATED_PLAYBOOK)
        validator = TestPlaybookValidator(structure)
        assert not validator.check_tasks_brands(self.ID_SET)

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

    def test_is_valid_brand_builtin_brand(self):
        """
        Given
            - brand name
            - id set
        When
            - brand_name is Builtin
        Then
            - return False
        """
        assert _is_valid_brand("Builtin", self.ID_SET)


if __name__ == '__main__':
    unittest.main()
