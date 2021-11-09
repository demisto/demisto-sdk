import unittest
from demisto_sdk.commands.common.hook_validations.common_playbook_validations import check_task_brand, _is_associated


def handle_error(error_message, error_code, file_path):
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

    def test_check_task_brand_good_brand(self):
        assert check_task_brand(self.ASSOCIATED_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_task_brand_no_id_set(self):
        assert check_task_brand(self.ASSOCIATED_PLAYBOOK, None, "some path", handle_error)

    def test_check_task_brand_no_tasks(self):
        assert check_task_brand(self.NO_TASKS_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_task_brand_no_specific_task(self):
        assert check_task_brand(self.TASK_MISSING_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_task_brand_no_script(self):
        assert check_task_brand(self.SCRIPT_MISSING_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_task_brand_no_pipes(self):
        assert check_task_brand(self.PIPES_MISSING_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_task_brand_bad_brand(self):
        assert not check_task_brand(self.NOT_ASSOCIATED_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_check_task_brand_no_brand(self):
        assert not check_task_brand(self.NO_NAME_ASSOCIATED_PLAYBOOK, self.ID_SET, "some path", handle_error)

    def test_is_associated_found_brand(self):
        assert _is_associated("rightname", self.ID_SET)

    def test_is_associated_not_found_brand(self):
        assert not _is_associated("wrongname", self.ID_SET)

    def test_is_associated_not_found_no_brand(self):
        assert not _is_associated("", self.ID_SET)


if __name__ == '__main__':
    unittest.main()
