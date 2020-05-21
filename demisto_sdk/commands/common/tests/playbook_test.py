from typing import Optional

import pytest
from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.tests.constants_test import (
    INVALID_PLAYBOOK_UNHANDLED_CONDITION,
    INVALID_TEST_PLAYBOOK_UNHANDLED_CONDITION)
from mock import patch


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
                                       'nexttasks': {'yes': ['3']}}}}
    CONDITION_EXIST_FULL_CASE_DIF = {"id": "Intezer - scan host", "version": -1,
                                     "tasks":
                                     {'1': {'type': 'condition',
                                            'conditions': [{'label': 'YES'}],
                                            'nexttasks': {'#default#': ['2'], 'yes': ['3']}}}}
    CONDITIONAL_ASK_EXISTS_NO_REPLY_OPTS = {"id": "Intezer - scan host", "version": -1,
                                            "tasks":
                                            {'1': {'type': 'condition',
                                                   'message': {},
                                                   'nexttasks': {}}}}
    CONDITIONAL_ASK_EXISTS_NO_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                          "tasks":
                                              {'1': {'type': 'condition',
                                                     'message': {'replyOptions': ['yes']},
                                                     'nexttasks': {}}}
                                          }
    CONDITIONAL_ASK_EXISTS_WITH_DFLT_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                                 "tasks":
                                                     {'1': {'type': 'condition',
                                                            'message': {'replyOptions': ['yes']},
                                                            'nexttasks': {'#default#': []}}}}
    CONDITIONAL_ASK_EXISTS_WITH_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                            "tasks":
                                                {'1': {'type': 'condition',
                                                       'message': {'replyOptions': ['yes']},
                                                       'nexttasks': {'yes': ['1']}}}
                                            }
    CONDITIONAL_ASK_EXISTS_WITH_NXT_TASK_CASE_DIF = {"id": "Intezer - scan host", "version": -1,
                                                     "tasks":
                                                     {'1': {'type': 'condition',
                                                            'message': {'replyOptions': ['yes']},
                                                            'nexttasks': {'YES': ['1']}}}}
    CONDITIONAL_SCRPT_WITHOUT_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                                "tasks":
                                                {'1': {'type': 'condition',
                                                       'scriptName': 'testScript'}}}
    CONDITIONAL_SCRPT_WITH_DFLT_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                            "tasks":
                                                {'1': {'type': 'condition',
                                                       'scriptName': 'testScript',
                                                       'nexttasks': {'#default#': []}}}}
    CONDITIONAL_SCRPT_WITH_MULTI_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                             "tasks":
                                                 {'1': {'type': 'condition',
                                                        'scriptName': 'testScript',
                                                        'nexttasks': {'#default#': [], 'yes': []}}}}
    IS_CONDITIONAL_INPUTS = [
        (CONDITION_NOT_EXIST_1, True),
        (CONDITION_EXIST_EMPTY_1, True),
        (CONDITION_EXIST_EMPTY_2, True),
        (CONDITION_EXIST_PARTIAL_1, True),
        (CONDITION_EXIST_PARTIAL_2, False),
        (CONDITION_EXIST_PARTIAL_3, False),
        (CONDITION_EXIST_FULL_NO_TASK_ID, False),
        (CONDITION_EXIST_FULL, True),
        (CONDITION_EXIST_FULL_CASE_DIF, True),
        (CONDITIONAL_ASK_EXISTS_NO_REPLY_OPTS, True),
        (CONDITIONAL_ASK_EXISTS_NO_NXT_TASK, False),
        (CONDITIONAL_ASK_EXISTS_WITH_DFLT_NXT_TASK, True),
        (CONDITIONAL_ASK_EXISTS_WITH_NXT_TASK, True),
        (CONDITIONAL_ASK_EXISTS_WITH_NXT_TASK_CASE_DIF, True),
        (CONDITIONAL_SCRPT_WITHOUT_NXT_TASK, False),
        (CONDITIONAL_SCRPT_WITH_DFLT_NXT_TASK, False),
        (CONDITIONAL_SCRPT_WITH_MULTI_NXT_TASK, True),
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
    IS_ROOT_CONNECTED_INPUTS = [
        (TASKS_NOT_EXIST, True),
        (NEXT_TASKS_NOT_EXIST_1, True),
        (NEXT_TASKS_NOT_EXIST_2, False),
        (NEXT_TASKS_INVALID_EXIST_1, False),
        (NEXT_TASKS_INVALID_EXIST_2, False),
        (NEXT_TASKS_VALID_EXIST_1, True),
        (NEXT_TASKS_VALID_EXIST_2, True),
    ]

    @pytest.mark.parametrize("playbook_json, expected_result", IS_NO_ROLENAME_INPUTS)
    def test_is_added_required_fields(self, playbook_json, expected_result):
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.is_no_rolename() is expected_result

    @pytest.mark.parametrize("playbook_json, expected_result", IS_CONDITIONAL_INPUTS)
    def test_is_condition_branches_handled(self, playbook_json, expected_result):
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.is_condition_branches_handled() is expected_result

    @pytest.mark.parametrize("playbook_json, expected_result", IS_ROOT_CONNECTED_INPUTS)
    def test_is_root_connected_to_all_tasks(self, playbook_json, expected_result):
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.is_root_connected_to_all_tasks() is expected_result

    @pytest.mark.parametrize("playbook_path, expected_result", [(INVALID_TEST_PLAYBOOK_UNHANDLED_CONDITION, True),
                                                                (INVALID_PLAYBOOK_UNHANDLED_CONDITION, False)])
    def test_skipping_test_playbooks(self, playbook_path, expected_result):
        """
            Given
            - A playbook

            When
            - The playbook has unhandled condition in it

            Then
            -  Ensure the unhandled condition is ignored if it's a test playbook
            -  Ensure validation fails if it's a not test playbook
        """
        structure = StructureValidator(file_path=playbook_path)
        validator = PlaybookValidator(structure)
        assert validator.is_valid_playbook() is expected_result
