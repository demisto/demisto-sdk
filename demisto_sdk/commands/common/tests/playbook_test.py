import pytest
from mock import patch
from typing import Optional
from demisto_sdk.commands.common.hook_validations.structure import StructureValidator
from demisto_sdk.commands.common.hook_validations.playbook import PlaybookValidator


def mock_structure(file_path=None, current_file=None, old_file=None):
    # type: (Optional[str], Optional[dict], Optional[dict]) -> StructureValidator
    with patch.object(StructureValidator, '__init__', lambda a, b: None):
        structure = StructureValidator(file_path)
        structure.is_valid = True
        structure.scheme_name = 'playbook'
        structure.file_path = file_path
        structure.current_file = current_file
        structure.old_file = old_file
        return structure


class TestPlaybookValidator:
    ROLENAME_NOT_EXIST = {"id": "Intezer - scan host", "version": -1}
    ROLENAME_EXIST_EMPTY = {"id": "Intezer - scan host", "version": -1, "rolename": []}
    ROLENAME_EXIST_NON_EMPTY = {"id": "Intezer - scan host", "version": -1, "rolename": ["Administrator"]}
    IS_NO_ROLENAME_INPUTS = [
        (ROLENAME_NOT_EXIST, True),
        (ROLENAME_EXIST_EMPTY, True),
        (ROLENAME_EXIST_NON_EMPTY, False)
    ]

    TASKS_NOT_EXIST = ROLENAME_NOT_EXIST
    NEXT_TASKS_NOT_EXIST_1 = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                              "tasks": {'1': {'type': 'not_condition'}}}
    NEXT_TASKS_NOT_EXIST_2 = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                              "tasks": {
                                  '1': {'type': 'title'},
                                  '2': {'type': 'condition'}}
                              }
    NEXT_TASKS_INVALID_EXIST_1 = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                                  "tasks": {
                                      '1': {'type': 'title', 'nexttasks': {'next': ['3']}},
                                      '2': {'type': 'condition'}}
                                  }
    NEXT_TASKS_INVALID_EXIST_2 = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                                  "tasks": {
                                      '1': {'type': 'title', 'nexttasks': {'next': ['3']}},
                                      '2': {'type': 'condition'},
                                      '3': {'type': 'condition'}}
                                  }
    NEXT_TASKS_VALID_EXIST_1 = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                                "tasks": {
                                    '1': {'type': 'title', 'nexttasks': {'next': ['2', '3']}},
                                    '2': {'type': 'condition'},
                                    '3': {'type': 'condition'}}
                                }
    NEXT_TASKS_VALID_EXIST_2 = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                                "tasks": {
                                    '1': {'type': 'title', 'nexttasks': {'next': ['2']}},
                                    '2': {'type': 'condition', 'nexttasks': {'next': ['3']}},
                                    '3': {'type': 'condition'}}
                                }

    @pytest.mark.parametrize("current_file, answer", IS_NO_ROLENAME_INPUTS)
    def test_is_added_required_fields(self, current_file, answer):
        structure = mock_structure("", current_file)
        validator = PlaybookValidator(structure)
        assert validator.is_no_rolename() is answer

    IS_ROOT_CONNECTED_INPUTS = [
        (TASKS_NOT_EXIST, True),
        (NEXT_TASKS_NOT_EXIST_1, True),
        (NEXT_TASKS_NOT_EXIST_2, False),
        (NEXT_TASKS_INVALID_EXIST_1, False),
        (NEXT_TASKS_INVALID_EXIST_2, False),
        (NEXT_TASKS_VALID_EXIST_1, True),
        (NEXT_TASKS_VALID_EXIST_2, True),
    ]

    @pytest.mark.parametrize("current_file, answer", IS_ROOT_CONNECTED_INPUTS)
    def test_is_root_connected_to_all_tasks(self, current_file, answer):
        structure = mock_structure("", current_file)
        validator = PlaybookValidator(structure)
        assert validator.is_root_connected_to_all_tasks() is answer
