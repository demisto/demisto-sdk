import pytest

from demisto_sdk.commands.content_graph.objects.base_playbook import TaskConfig
from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.validators.PB_validators.PB100_is_no_rolename import (
    IsNoRolenameValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB101_is_playbook_has_unreachable_condition import (
    IsAskConditionHasUnreachableConditionValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB103_does_playbook_have_unconnected_tasks import (
    ERROR_MSG,
    DoesPlaybookHaveUnconnectedTasks,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB104_deprecated_description import (
    DeprecatedDescriptionValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB105_playbook_delete_context_all import (
    PlaybookDeleteContextAllValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB108_is_valid_task_id import (
    IsValidTaskIdValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks import (
    IsInputKeyNotInTasksValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB123_is_conditional_task_has_unhandled_reply_options import (
    IsAskConditionHasUnhandledReplyOptionsValidator,
)


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(
                paths=["inputs", "tasks.0.task.key"],
                values=[
                    [{"key": "input_name1", "value": "input_value1"}],
                    {"first_input": "inputs.input_name1"},
                ],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["inputs", "tasks.0.task.key"],
                values=[
                    [{"key": "input_name1", "value": "input_value1"}],
                    {
                        "first_input": "inputs.input_name1",
                        "second_input": "inputs.input_name2",
                    },
                ],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["inputs", "tasks.0.task.key"],
                values=[
                    [{"key": "input_name2", "value": "input_value2"}],
                    {"first_input": "inputs.input_name1"},
                ],
            ),
            "The playbook 'Detonate File - JoeSecurity V2' contains the following inputs that are not used in any of its tasks: input_name2",
        ),
    ],
)
def test_is_valid_all_inputs_in_use(content_item, expected_result):
    """
    Given:
    - A playbook with inputs in some tasks and inputs defined in the inputs section
        Case 1: All inputs defined in the inputs section are in use in the playbook
        Case 2: All inputs defined in the inputs section are in use in the playbook but not all inputs in use are defined in the inputs section
        Case 3: All inputs defined in the inputs section are not in use in the playbook

    When:
    - Validating the playbook

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is valid since all inputs defined in the inputs section are in use in the playbook
        Case 3: The playbook is invalid
    """
    result = IsInputKeyNotInTasksValidator().is_valid([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
    )


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(),
            [],
        ),
        (
            create_playbook_object(
                paths=["rolename"],
                values=[[]],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["rolename"],
                values=[["Administrator"]],
            ),
            "The playbook 'Detonate File - JoeSecurity V2' can not have a rolename, please remove the field.",
        ),
    ],
)
def test_is_no_rolename(content_item, expected_result):
    """
    Given:
    - A playbook with id
        Case 1: The playbook has only id and no rolename.
        Case 2: The playbook has id and an empty rolename.
        Case 3: The playbook has id and rolename.

    When:
    - Validating the playbook

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is invalid
        Case 3: The playbook is invalid
    """
    result = IsNoRolenameValidator().is_valid([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
    )


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(
                paths=["deprecated", "description"],
                values=[True, "Deprecated. Use <PLAYBOOK_NAME> instead."],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["deprecated", "description"],
                values=[True, "Deprecated. <REASON> No available replacement."],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["deprecated", "description"],
                values=[True, "Not a valid description"],
            ),
            "The deprecated playbook 'Detonate File - JoeSecurity V2' has invalid description.\nThe description of "
            'all deprecated playbooks should follow one of the formats:\n1. "Deprecated. Use <PLAYBOOK_NAME> '
            'instead."\n2. "Deprecated. <REASON> No available replacement."',
        ),
    ],
)
def test_is_deprecated_with_invalid_description(content_item, expected_result):
    """
    Given:
    - A playbook with id
        Case 1: The playbook is deprecated and has valid description.
        Case 2: The playbook is deprecated and has valid description.
        Case 3: The playbook is deprecated and has invalid description.

    When:
    - calling DeprecatedDescriptionValidator.is_valid.

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is valid
        Case 3: The playbook is invalid
    """
    result = DeprecatedDescriptionValidator().is_valid([content_item])

    assert (
        result == expected_result
        if isinstance(expected_result, list)
        else result[0].message == expected_result
    )


def test_IsAskConditionHasUnreachableConditionValidator():
    playbook = create_playbook_object()
    assert not IsAskConditionHasUnreachableConditionValidator().is_valid([playbook])
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "test task",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "type": "condition",
                "message": {"replyOptions": ["yes"]},
                "nexttasks": {"no": ["1"], "yes": ["2"]},
                "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
            }
        )
    }
    assert IsAskConditionHasUnreachableConditionValidator().is_valid([playbook])


def test_IsAskConditionHasUnhandledReplyOptionsValidator():
    playbook = create_playbook_object()
    assert not IsAskConditionHasUnhandledReplyOptionsValidator().is_valid([playbook])
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "test task",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "type": "condition",
                "message": {"replyOptions": ["yes"]},
                "nexttasks": {"no": ["1"]},
                "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
            }
        )
    }
    assert IsAskConditionHasUnhandledReplyOptionsValidator().is_valid([playbook])


def create_invalid_playbook(field: str):
    """Create an invalid playbook that has an invalid taskid or the 'id' under the 'task' field is invalid
    Args:
        - field str: which field to update taskid or task.id.
    Return:
        - a playbook object
    """
    playbook = create_playbook_object()
    tasks = playbook.tasks
    for task_id in tasks:
        task_obj = tasks[task_id]
        if field == "taskid":
            task_obj.taskid = task_obj.taskid + "1234"
        else:
            task_obj.task.id = task_obj.task.id + "1234"
        break
    return playbook


def test_IsValidTaskIdValidator(playbook):
    """
    Given:
    - A playbook
        Case 1: The playbook is valid.
        Case 2: The playbook isn't valid, it has invalid taskid.
        Case 3: The playbook isn't valid, the 'id' under the 'task' field is invalid.

    When:
    - calling IsValidTaskIdValidator.is_valid.

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid
        Case 2: The playbook is invalid
        Case 3: The playbook is invalid
    """
    # Case 1
    playbook_valid = create_playbook_object()
    results_valid = IsValidTaskIdValidator().is_valid([playbook_valid])

    # Case 2
    playbook_invalid_taskid = create_invalid_playbook("taskid")
    results_invalid_taskid = IsValidTaskIdValidator().is_valid(
        [playbook_invalid_taskid]
    )

    # Case 3
    playbook_invalid_id = create_invalid_playbook("id")
    results_invalid_id = IsValidTaskIdValidator().is_valid([playbook_invalid_id])

    assert not results_valid
    assert results_invalid_taskid
    assert results_invalid_id


def test_PlaybookDeleteContextAllValidator():
    """
    Given:
    - A playbook with tasks.
    Case 1: The playbook is valid - test with the default playbook object.
    Case 2: The playbook is invalid, with DeleteContext with all set to 'Yes'
    -

    When:
    - calling PlaybookDeleteContextAllValidator.is_valid.

    Then:
    - The results should be as expected:
        Case 1: The playbook is valid.
        Case 2: The playbook is invalid.
    """
    playbook = create_playbook_object()
    assert not PlaybookDeleteContextAllValidator().is_valid([playbook])
    playbook.tasks = {
        "0": TaskConfig(
            **{
                "id": "test task",
                "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                "type": "condition",
                "message": {"replyOptions": ["yes"]},
                "nexttasks": {"no": ["1"], "yes": ["2"]},
                "task": {
                    "id": "task-id",
                    "name": "DeleteContext",
                    "scriptName": "DeleteContext",
                },
                "scriptarguments": {"all": {"simple": "yes"}},
            }
        )
    }
    expected_result = (
        "The playbook includes DeleteContext tasks with all set to 'yes', which is not permitted."
        " Please correct the following tasks: ['task-id']"
        " For more info, see:"
        " https://xsoar.pan.dev/docs/playbooks/playbooks-overview#inputs-and-outputs"
    )

    assert (
        PlaybookDeleteContextAllValidator().is_valid([playbook])[0].message
        == expected_result
    )


def test_does_playbook_have_unconnected_tasks():
    """
    Given: A playbook with tasks that are connected to each other.
    When: Validating the playbook.
    Then: The playbook is valid.
    """
    playbook = create_playbook_object(
        paths=["starttaskid", "tasks"],
        values=[
            "0",
            {
                "0": {
                    "id": "test task",
                    "type": "regular",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"#none#": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                },
                "1": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
            },
        ],
    )
    validation_results = DoesPlaybookHaveUnconnectedTasks().is_valid([playbook])
    assert len(validation_results) == 0  # No validation results should be returned


def test_does_playbook_have_unconnected_tasks_not_valid():
    """
    Given: A playbook with tasks that are not connected to the root task.
    When: Validating the playbook.
    Then: The playbook is not valid.
    """
    playbook = create_playbook_object(
        paths=["starttaskid", "tasks"],
        values=[
            "0",
            {
                "0": {
                    "id": "test task",
                    "type": "regular",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"#none#": ["1"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a631",
                },
                "1": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
                "3": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
                "4": {
                    "id": "test task",
                    "type": "condition",
                    "message": {"replyOptions": ["yes"]},
                    "nexttasks": {"no": ["2"]},
                    "task": {"id": "27b9c747-b883-4878-8b60-7f352098a63c"},
                    "taskid": "27b9c747-b883-4878-8b60-7f352098a632",
                },
            },
        ],
    )
    orphan_tasks = ["3", "4"]
    validation_result = DoesPlaybookHaveUnconnectedTasks().is_valid([playbook])
    assert validation_result
    assert validation_result[0].message == ERROR_MSG.format(orphan_tasks=orphan_tasks)
