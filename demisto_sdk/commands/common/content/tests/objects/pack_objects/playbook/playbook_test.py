import pytest
from demisto_sdk.commands.common.content.objects.pack_objects import Playbook
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.tests.constants_test import (
    INVALID_PLAYBOOK_UNHANDLED_CONDITION,
    INVALID_TEST_PLAYBOOK_UNHANDLED_CONDITION)

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'


def mock_playbook(repo):
    pack = repo.create_pack('Temp')
    playbook = pack.create_playbook(name='MyPlaybook')
    playbook.create_default_playbook()
    return playbook


def test_objects_factory(repo):
    playbook = mock_playbook(repo)
    obj = path_to_pack_object(playbook.yml.path)
    assert isinstance(obj, Playbook)


def test_prefix(repo):
    playbook = mock_playbook(repo)
    obj = Playbook(playbook.yml.path)
    assert obj.normalize_file_name() == 'playbook-MyPlaybook.yml'


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


@pytest.mark.parametrize("playbook_json, id_set_json, expected_result", IS_SCRIPT_ID_VALID)
def test_playbook_script_id(repo, playbook_json, id_set_json, expected_result):
    """

    Given
    - A playbook with scrips ids or script names
    - An id_set file.

    When
    - validating playbook

    Then
    - In case script id or script name don't exist in id_set , prints a warning.
    """
    playbook = mock_playbook(repo)
    playbook.yml.write_dict(playbook_json)
    base = BaseValidator(id_set_file=id_set_json)
    playbook_obj = Playbook(playbook.yml.path, base)
    assert playbook_obj.is_script_id_valid() == expected_result


@pytest.mark.parametrize("playbook_json, expected_result", IS_NO_ROLENAME_INPUTS)
def test_is_added_required_fields(playbook_json, expected_result, repo):
    playbook = mock_playbook(repo)
    playbook.yml.write_dict(playbook_json)
    playbook_obj = Playbook(playbook.yml.path)
    assert playbook_obj.is_no_rolename() is expected_result


@pytest.mark.parametrize("playbook_json, expected_result", IS_CONDITIONAL_INPUTS)
def test_is_condition_branches_handled(playbook_json, expected_result, repo):
    playbook = mock_playbook(repo)
    playbook.yml.write_dict(playbook_json)
    playbook_obj = Playbook(playbook.yml.path)
    assert playbook_obj.is_condition_branches_handled() is expected_result


@pytest.mark.parametrize("playbook_json, expected_result", IS_ROOT_CONNECTED_INPUTS)
def test_is_root_connected_to_all_tasks(playbook_json, expected_result, repo):
    playbook = mock_playbook(repo)
    playbook.yml.write_dict(playbook_json)
    playbook_obj = Playbook(playbook.yml.path)
    assert playbook_obj.is_root_connected_to_all_tasks() is expected_result


@pytest.mark.parametrize("playbook_path, expected_result", [(INVALID_TEST_PLAYBOOK_UNHANDLED_CONDITION, True),
                                                            (INVALID_PLAYBOOK_UNHANDLED_CONDITION, False)])
def test_skipping_test_playbooks(mocker, playbook_path, expected_result):
    """
        Given
        - A playbook

        When
        - The playbook has unhandled condition in it

        Then
        -  Ensure the unhandled condition is ignored if it's a test playbook
        -  Ensure validation fails if it's a not test playbook
    """
    playbook_obj = Playbook(playbook_path)
    mocker.patch.object(playbook_obj, 'is_script_id_valid', return_value=True)
    assert playbook_obj.is_valid_playbook() is expected_result


@pytest.mark.parametrize("playbook_json, expected_result", IS_DELETECONTEXT)
def test_is_delete_context_all_in_playbook(playbook_json, expected_result, repo):
    """
    Given
    - A playbook

    When
    - The playbook have deleteContext script use with all=yes

    Then
    -  Ensure that the validation fails when all=yes arg exists.
    """
    playbook = mock_playbook(repo)
    playbook.yml.write_dict(playbook_json)
    playbook_obj = Playbook(playbook.yml.path)
    assert playbook_obj.is_delete_context_all_in_playbook() is expected_result


@pytest.mark.parametrize("playbook_json, expected_result", IS_USING_INSTANCE)
def test_is_using_instance(playbook_json, expected_result, repo):
    """
    Given
    - A playbook

    When
    - The playbook has a using specific instance.
    - The playbook doestnt have using in it.

    Then
    - Ensure validation fails if it's a not test playbook
    - Ensure that the validataion passes if no using usage.
    """
    playbook = mock_playbook(repo)
    playbook.yml.write_dict(playbook_json)
    playbook_obj = Playbook(playbook.yml.path)
    assert playbook_obj.is_using_instance() is expected_result
