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
    CONDITION_NOT_EXIST_1 = ROLENAME_NOT_EXIST
    CONDITION_NOT_EXIST_2 = {"id": "Intezer - scan host", "version": -1, "tasks": {'1': {'type': 'not_condition'}}}
    CONDITION_EXIST_EMPTY_1 = {"id": "Intezer - scan host", "version": -1,
                               "tasks": {
                                   '1': {'type': 'not_condition'},
                                   '2': {'type': 'condition'}}
                               }
    CONDITION_EXIST_EMPTY_2 = {"id": "Intezer - scan host", "version": -1,
                               "tasks":
                                   {'1': {'type': 'condition',
                                          'nexttasks': {}}}
                               }
    CONDITION_EXIST_PARTIAL_1 = {"id": "Intezer - scan host", "version": -1,
                                 "tasks":
                                     {'1': {'type': 'condition',
                                            'conditions': [],
                                            'nexttasks': {}}}
                                 }
    CONDITION_EXIST_PARTIAL_2 = {"id": "Intezer - scan host", "version": -1,
                                 "tasks":
                                     {'1':
                                          {'type': 'condition',
                                           'conditions': [{'label': 'yes'}],
                                           'nexttasks': {'#default#': ['2']}}}
                                 }
    CONDITION_EXIST_PARTIAL_3 = {"id": "Intezer - scan host", "version": -1,
                                 "tasks":
                                     {'1': {'type': 'condition',
                                            'conditions': [{'label': 'yes'}],
                                            'nexttasks': {'#default#': []}}}
                                 }
    CONDITION_EXIST_FULL_NO_TASK_ID = {"id": "Intezer - scan host", "version": -1,
                                       "tasks":
                                           {'1': {'type': 'condition',
                                                  'conditions': [{'label': 'yes'}],
                                                  'nexttasks': {'#default#': []}}}
                                       }
    CONDITION_EXIST_FULL = {"id": "Intezer - scan host", "version": -1,
                            "tasks":
                                {'1': {'type': 'condition',
                                       'conditions': [{'label': 'yes'}],
                                       'nexttasks': {'#default#': ['2'], 'yes': ['3']}}}
                            }
    IS_CONDITIONAL_INPUTS = [
        (CONDITION_NOT_EXIST_1, True),
        (CONDITION_EXIST_EMPTY_1, False),
        (CONDITION_EXIST_EMPTY_2, False),
        (CONDITION_EXIST_PARTIAL_1, False),
        (CONDITION_EXIST_PARTIAL_2, False),
        (CONDITION_EXIST_PARTIAL_3, False),
        (CONDITION_EXIST_FULL_NO_TASK_ID, False),
        (CONDITION_EXIST_FULL, True)
    ]

    @pytest.mark.parametrize("current_file, answer", IS_NO_ROLENAME_INPUTS)
    def test_is_added_required_fields(self, current_file, answer):
        structure = mock_structure("", current_file)
        validator = PlaybookValidator(structure)
        assert validator.is_no_rolename() is answer

    @pytest.mark.parametrize("current_file, answer", IS_CONDITIONAL_INPUTS)
    def test_is_condition_branches_handled_correctly(self, current_file, answer):
        structure = mock_structure("", current_file)
        validator = PlaybookValidator(structure)
        assert validator.is_condition_branches_handled_correctly() is answer
