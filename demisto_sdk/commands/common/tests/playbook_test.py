from typing import Optional

import pytest
from demisto_sdk.commands.common.hook_validations.playbook import \
    PlaybookValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.tests.constants_test import (
    CONTENT_REPO_EXAMPLE_ROOT, INVALID_PLAYBOOK_UNHANDLED_CONDITION,
    INVALID_TEST_PLAYBOOK_UNHANDLED_CONDITION)
from mock import patch
from TestSuite.test_tools import ChangeCWD


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
                                     {'1': {'type': 'condition',
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
    DELETECONTEXT_ALL_EXIST = {"id": "Intezer - scan host", "version": -1,
                               "tasks":
                                   {'1': {'type': 'regular',
                                          'task': {'scriptName': 'DeleteContext'},
                                          'scriptarguments': {'all': {'simple': 'yes'}}}}}
    DELETECONTEXT_WITHOUT_ALL = {"id": "Intezer - scan host", "version": -1,
                                 "tasks":
                                     {'1': {'type': 'regular',
                                            'task': {'scriptName': 'DeleteContext'},
                                            'scriptarguments': {'all': {'simple': 'no'}}}}}
    DELETECONTEXT_DOESNT_EXIST = {"id": "Intezer - scan host", "version": -1,
                                  "tasks":
                                      {'1': {'type': 'regular',
                                             'task': {'name': 'test'}}}}
    IS_DELETECONTEXT = [
        (DELETECONTEXT_ALL_EXIST, False),
        (DELETECONTEXT_WITHOUT_ALL, True),
        (DELETECONTEXT_DOESNT_EXIST, True)
    ]

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

    IS_INSTANCE_EXISTS = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                          "tasks": {
                              '1': {'type': 'title', 'nexttasks': {'next': ['2']},
                                    'scriptarguments': {'using': {'simple': 'tst.instance'}}},
                              '2': {'type': 'condition', 'nexttasks': {'next': ['3']}},
                              '3': {'type': 'condition'}}
                          }

    IS_INSTANCE_DOESNT_EXISTS = {"id": "Intezer - scan host", "version": -1, "starttaskid": "1",
                                 "tasks": {
                                     '1': {'type': 'title', 'nexttasks': {'next': ['2', '3']}},
                                     '2': {'type': 'condition'},
                                     '3': {'type': 'condition'}}
                                 }

    IS_USING_INSTANCE = [
        (IS_INSTANCE_EXISTS, False),
        (IS_INSTANCE_DOESNT_EXISTS, True),
    ]

    IS_ROOT_CONNECTED_INPUTS = [
        (TASKS_NOT_EXIST, True),
        (NEXT_TASKS_NOT_EXIST_1, True),
        (NEXT_TASKS_NOT_EXIST_2, False),
        (NEXT_TASKS_INVALID_EXIST_1, False),
        (NEXT_TASKS_INVALID_EXIST_2, False),
        (NEXT_TASKS_VALID_EXIST_1, True),
        (NEXT_TASKS_VALID_EXIST_2, True),
    ]

    PLAYBOOK_JSON_VALID_SCRIPT_ID = {
        "tasks": {"0": {"task": {"script": "scriptId1"}},
                  "1": {"task": {"script": "scriptId2"}}}}
    ID_SET_VALID_SCRIPT_ID = {"scripts": [{"scriptId1": {"name": "name"}}, {"scriptId2": {"name": "name"}}]}

    PLAYBOOK_JSON_INVALID_SCRIPT_ID = {
        "tasks": {"0": {"task": {"script": "scriptId1"}},
                  "1": {"task": {"script": "scriptId2"}}}}
    ID_SET_INVALID_SCRIPT_ID = {"scripts": [{"scriptId2": {"name": "name"}}]}

    PLAYBOOK_JSON_VALID_SCRIPT_NAME = {
        "tasks": {"0": {"task": {"scriptName": "scriptName1"}},
                  "1": {"task": {"scriptName": "scriptName2"}}}}
    ID_SET_VALID_SCRIPT_NAME = {
        "scripts": [{"scriptId1": {"name": "scriptName1"}}, {"scriptId2": {"name": "scriptName2"}}]}

    PLAYBOOK_JSON_INVALID_SCRIPT_NAME = {
        "tasks": {"0": {"task": {"scriptName": "scriptName1"}},
                  "1": {"task": {"scriptName": "scriptName2"}}}}
    ID_SET_INVALID_SCRIPT_NAME = {
        "scripts": [{"scriptId1": {"name": "scriptName3"}}, {"scriptId2": {"name": "scriptName1"}}]}

    IS_SCRIPT_ID_VALID = [
        (PLAYBOOK_JSON_VALID_SCRIPT_ID, ID_SET_VALID_SCRIPT_ID, True),
        (PLAYBOOK_JSON_INVALID_SCRIPT_ID, ID_SET_INVALID_SCRIPT_ID, False),
        (PLAYBOOK_JSON_VALID_SCRIPT_NAME, ID_SET_VALID_SCRIPT_NAME, True),
        (PLAYBOOK_JSON_INVALID_SCRIPT_NAME, ID_SET_INVALID_SCRIPT_NAME, False),
    ]

    PLAYBOOK_JSON_VALID_SUB_PB_NAME = {
        "tasks": {"0": {"task": {"playbookName": "playbookId1"}},
                  "1": {"task": {"playbookName": "playbookId2"}}}}
    ID_SET_VALID_SUB_PB_ID = {"playbooks": [{"playbookId1": {"name": "name"}}, {"playbookId2": {"name": "name"}}]}

    PLAYBOOK_JSON_INVALID_SUB_PB_NAME = {
        "tasks": {"0": {"task": {"playbookName": "playbookId1 "}},
                  "1": {"task": {"playbookName": "playbookId2"}}}}
    ID_SET_INVALID_SUB_PB_ID = {"playbooks": [{"playbookId2": {"name": "name"}}]}

    IS_SUB_PLAYBOOK_ID_VALID = [
        (PLAYBOOK_JSON_VALID_SUB_PB_NAME, ID_SET_VALID_SUB_PB_ID, True),
        (PLAYBOOK_JSON_VALID_SUB_PB_NAME, ID_SET_INVALID_SUB_PB_ID, False),
        (PLAYBOOK_JSON_INVALID_SUB_PB_NAME, ID_SET_VALID_SUB_PB_ID, False)
    ]
    PlAYBOOK_JSON_VALID_TASKID = {
        "0": {"task": {"id": "8bff5d33-9554-4ab9-833c-cc0c0d5fdfd8"},
              "taskid": "8bff5d33-9554-4ab9-833c-cc0c0d5fdfd8"},
        "1": {"task": {"id": "106b8f2e-5106-4857-82ac-122450af4893"},
              "taskid": "106b8f2e-5106-4857-82ac-122450af4893"}
    }

    PlAYBOOK_JSON_INVALID_TASKID = {
        "0": {"task": {"id": "1"},
              "taskid": "1"},
        "1": {"task": {"id": "106b8f2e-5106-4857-82ac-122450af4893"},
              "taskid": "106b8f2e-5106-4857-82ac-122450af4893"}
    }

    PLAYBOOK_JSON_ID_EQUALS_TASKID = {
        "0": {"task": {"id": "8bff5d33-9554-4ab9-833c-cc0c0d5fdfd8"},
              "taskid": "8bff5d33-9554-4ab9-833c-cc0c0d5fdfd8"},
        "1": {"task": {"id": "106b8f2e-5106-4857-82ac-122450af4893"},
              "taskid": "106b8f2e-5106-4857-82ac-122450af4893"}
    }

    PLAYBOOK_JSON_ID_NOT_EQUAL_TO_TASKID = {
        "0": {"task": {"id": "8bff5d33-9554-4ab9-833c-cc0c0d5fdfd8"},
              "taskid": "106b8f2e-5106-4857-82ac-122450af4893"},
        "1": {"task": {"id": "106b8f2e-5106-4857-82ac-122450af4893"},
              "taskid": "8bff5d33-9554-4ab9-833c-cc0c0d5fdfd8"}
    }

    IS_ID_UUID = [
        (PlAYBOOK_JSON_VALID_TASKID, True),
        (PlAYBOOK_JSON_INVALID_TASKID, False)
    ]

    IS_TASK_ID_EQUALS_ID = [
        (PLAYBOOK_JSON_ID_EQUALS_TASKID, True),
        (PLAYBOOK_JSON_ID_NOT_EQUAL_TO_TASKID, False)
    ]

    DEPRECATED_VALID = {"deprecated": True, "description": "Deprecated. Use the XXXX playbook instead."}
    DEPRECATED_VALID2 = {"deprecated": True, "description": "Deprecated. Feodo Tracker no longer supports this feed "
                                                            "No available replacement."}
    DEPRECATED_VALID3 = {"deprecated": True, "description": "Deprecated. The playbook uses an unsupported scraping"
                                                            " API. Use Proofpoint Protection Server v2 playbook"
                                                            " instead."}

    DEPRECATED_INVALID_DESC = {"deprecated": True, "description": "Deprecated."}
    DEPRECATED_INVALID_DESC2 = {"deprecated": True, "description": "Use the ServiceNow playbook to manage..."}
    DEPRECATED_INVALID_DESC3 = {"deprecated": True, "description": "Deprecated. The playbook uses an unsupported"
                                                                   " scraping API."}
    DEPRECATED_INPUTS = [
        (DEPRECATED_VALID, True),
        (DEPRECATED_VALID2, True),
        (DEPRECATED_VALID3, True),
        (DEPRECATED_INVALID_DESC, False),
        (DEPRECATED_INVALID_DESC2, False),
        (DEPRECATED_INVALID_DESC3, False)
    ]

    CONDITIONAL_SCRPT_WITH_DFLT_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                            "tasks":
                                                {'1': {'type': 'condition',
                                                       'scriptName': 'testScript',
                                                       'nexttasks': {'#default#': []}}}}

    CONDITIONAL_SCRPT_WITH_NO_DFLT_NXT_TASK = {"id": "Intezer - scan host", "version": -1,
                                               "tasks":
                                               {'1': {'type': 'condition',
                                                      'scriptName': 'testScript',
                                                      'nexttasks': {'1': []}}}}

    CONDITION_TASK_WITH_ELSE = {'1': {'type': 'condition',
                                      'scriptName': 'testScript',
                                      'nexttasks': {'#default#': []}}}

    CONDITION_TASK_WITHOUT_ELSE = {'1': {'type': 'condition',
                                         'scriptName': 'testScript',
                                                       'nexttasks': {'1': []}}}
    IS_ELSE_IN_CONDITION_TASK = [(CONDITIONAL_SCRPT_WITH_NO_DFLT_NXT_TASK.get('tasks').get('1'), False),
                                 (CONDITIONAL_SCRPT_WITH_DFLT_NXT_TASK.get('tasks').get('1'), True)]

    @pytest.mark.parametrize("playbook_json, id_set_json, expected_result", IS_SCRIPT_ID_VALID)
    def test_playbook_script_id(self, mocker, playbook, repo, playbook_json, id_set_json, expected_result):
        """

        Given
        - A playbook with scrips ids or script names
        - An id_set file.

        When
        - validating playbook

        Then
        - In case script id or script name don't exist in id_set , prints a warning.
        """
        playbook.yml.write_dict(playbook_json)
        repo.id_set.write_json(id_set_json)
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.is_script_id_valid(id_set_json) == expected_result

    @pytest.mark.parametrize("playbook_json, id_set_json, expected_result", IS_SUB_PLAYBOOK_ID_VALID)
    def test_playbook_sub_playbook_id(self, mocker, playbook, repo, playbook_json, id_set_json, expected_result):
        """

        Given
        - A playbook with playbook names
        - An id_set file.

        When
        - validating playbook

        Then
        - In case playbook name does not exist in id_set , prints a warning.
        """
        playbook.yml.write_dict(playbook_json)
        repo.id_set.write_json(id_set_json)
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.is_subplaybook_name_valid(id_set_json) == expected_result

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
    def test_skipping_test_playbooks(self, mocker, playbook_path, expected_result):
        """
            Given
            - A playbook

            When
            - The playbook has unhandled condition in it

            Then
            -  Ensure the unhandled condition is ignored if it's a test playbook
            -  Ensure validation fails if it's a not test playbook
        """
        with ChangeCWD(CONTENT_REPO_EXAMPLE_ROOT):
            structure = StructureValidator(file_path=playbook_path)
            validator = PlaybookValidator(structure)
            mocker.patch.object(validator, 'is_script_id_valid', return_value=True)

            assert validator.is_valid_playbook() is expected_result

    @pytest.mark.parametrize("playbook_json, expected_result", IS_DELETECONTEXT)
    def test_is_delete_context_all_in_playbook(self, playbook_json, expected_result):
        """
        Given
        - A playbook

        When
        - The playbook have deleteContext script use with all=yes

        Then
        -  Ensure that the validation fails when all=yes arg exists.
        """
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.is_delete_context_all_in_playbook() is expected_result

    @pytest.mark.parametrize("playbook_json, expected_result", IS_USING_INSTANCE)
    def test_is_using_instance(self, playbook_json, expected_result):
        """
        Given
        - A playbook

        When
        - The playbook has a using specific instance.
        - The playbook doestnt have using in it.

        Then
        - Ensure validation fails if it's a not test playbook
        - Ensure that the validation passes if no using usage.
        """
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.is_using_instance() is expected_result

    @pytest.mark.parametrize("playbook_json, expected_result", IS_ID_UUID)
    def test_is_id_uuid(self, playbook_json, expected_result):
        """
        Given
        - A playbook

        When
        - The playbook include taskid and inside task field an id that are both from uuid type.
        - The playbook include taskid and inside task field an id that are not both from uuid type.

        Then
        - Ensure validation passes if the taskid field and the id inside task field are both from uuid type
        - Ensure validation fails if the taskid field and the id inside task field are one of them not from uuid type
        """
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        validator._is_id_uuid() is expected_result

    @pytest.mark.parametrize("playbook_json, expected_result", IS_TASK_ID_EQUALS_ID)
    def test_is_taskid_equals_id(self, playbook_json, expected_result):
        """
        Given
        - A playbook

        When
        - The playbook include taskid and inside task field an id that are both have the same value.
        - The playbook include taskid and inside task field an id that are different values.

        Then
        - Ensure validation passes if the taskid field and the id inside task field have the same value
        - Ensure validation fails if the taskid field and the id inside task field are have different value
        """
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        validator._is_taskid_equals_id() is expected_result

    @pytest.mark.parametrize("current, answer", DEPRECATED_INPUTS)
    def test_is_valid_deprecated_playbook(self, current, answer):
        """
        Given
            1. A deprecated playbook with a valid description according to 'deprecated regex' (including the replacement
               playbook name).
            2. A deprecated playbook with a valid description according to the 'deprecated no replacement regex'.
            3. A deprecated playbook with a valid description according to 'deprecated regex' (including the replacement
               playbook name, and the reason for deprecation.).
            4. A deprecated playbook with an invalid description that isn't according to the 'deprecated regex'
               (doesn't include a replacement playbook name, or declare there isn't a replacement).
            5. A deprecated playbook with an invalid description that isn't according to the 'deprecated regex'
               (doesn't start with the phrase: 'Deprecated.').
            6. A deprecated playbook with an invalid description that isn't according to the 'deprecated regex'
               (Includes the reason for deprecation, but doesn't include a replacement playbook name,
               or declare there isn't a replacement).
        When
            - running is_valid_as_deprecated.

        Then
            - a playbook with an invalid description will be errored.
        """
        structure = mock_structure("", current)
        validator = PlaybookValidator(structure)
        validator.current_file = current
        assert validator.is_valid_as_deprecated() is answer

    @pytest.mark.parametrize("playbook_json, expected_result", [(CONDITIONAL_SCRPT_WITH_NO_DFLT_NXT_TASK, True)])
    def test_verify_all_conditional_tasks_has_else_path(self, playbook_json, expected_result):
        """
        Given
            - A playbook with a condition without a default task

        When
            - Running Validate playbook

        Then
            - Function returns true as this is an ignored error.
        """
        structure = mock_structure("", playbook_json)
        validator = PlaybookValidator(structure)
        assert validator.verify_condition_tasks_has_else_path() is expected_result

    @pytest.mark.parametrize("playbook_task_json, expected_result", IS_ELSE_IN_CONDITION_TASK)
    def test_verify_else_for_conditions_task(self, playbook_task_json, expected_result):
        """
        Given
            - A playbook condition task with a default task
            - A playbook condition task without a default task

        When
            - Running Validate playbook

        Then
            - Return True if the condition task has default path , else false
        """
        structure = mock_structure("", playbook_task_json)
        validator = PlaybookValidator(structure)
        assert validator._is_else_path_in_condition_task(task=playbook_task_json) is expected_result

    def test_name_contains_the_type(self, pack):
        """
        Given
            - An playbook with a name that contains the word "playbook".
        When
            - running name_not_contain_the_type.
        Then
            - Ensure the validate failed.
        """
        playbook = pack.create_playbook(yml={"name": "test_playbook"})

        with ChangeCWD(pack.repo_path):
            structure_validator = StructureValidator(playbook.yml.path)
            validator = PlaybookValidator(structure_validator)

            assert not validator.name_not_contain_the_type()

    def test_name_does_not_contains_the_type(self, pack):
        """
        Given
            - An playbook with a name that does not contains the "playbook" string.
        When
            - running name_not_contain_the_type.
        Then
            - Ensure the validate passes.
        """
        playbook = pack.create_playbook(yml={"name": "test"})

        with ChangeCWD(pack.repo_path):
            structure_validator = StructureValidator(playbook.yml.path)
            validator = PlaybookValidator(structure_validator)

            assert validator.name_not_contain_the_type()
