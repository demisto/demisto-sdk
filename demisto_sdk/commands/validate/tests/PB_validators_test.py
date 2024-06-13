import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.validators.PB_validators.PB100_is_no_rolename import (
    IsNoRolenameValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB101_is_playbook_has_unreachable_condition import (
    IsAskConditionHasUnreachableConditionValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB103_is_playbook_has_unconnected_tasks import (
    IsPlaybookHasUnconnectedTasks,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB104_deprecated_description import (
    DeprecatedDescriptionValidator,
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
                paths=["inputs", "tasks"],
                values=[
                    [{"key": "input_name1", "value": "input_value1"}],
                    {"key": {"first_input": "inputs.input_name1"}},
                ],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["inputs", "tasks"],
                values=[
                    [{"key": "input_name1", "value": "input_value1"}],
                    {
                        "key": {
                            "first_input": "inputs.input_name1",
                            "second_input": "inputs.input_name2",
                        }
                    },
                ],
            ),
            [],
        ),
        (
            create_playbook_object(
                paths=["inputs", "tasks"],
                values=[
                    [{"key": "input_name2", "value": "input_value2"}],
                    {"key": {"first_input": "inputs.input_name1"}},
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
        "0": {
            "id": "test task",
            "type": "condition",
            "message": {"replyOptions": ["yes"]},
            "nexttasks": {"no": ["1"], "yes": ["2"]},
        }
    }
    assert IsAskConditionHasUnreachableConditionValidator().is_valid([playbook])


def test_IsAskConditionHasUnhandledReplyOptionsValidator():
    playbook = create_playbook_object()
    assert not IsAskConditionHasUnhandledReplyOptionsValidator().is_valid([playbook])
    playbook.tasks = {
        "0": {
            "id": "test task",
            "type": "condition",
            "message": {"replyOptions": ["yes"]},
            "nexttasks": {"no": ["1"]},
        }
    }
    assert IsAskConditionHasUnhandledReplyOptionsValidator().is_valid([playbook])


def test_is_playbook_has_unconnected_tasks():
    """
    Given: A playbook with tasks that are connected to each other.
    When: Validating the playbook.
    Then: The playbook is valid.
    """
    playbook = create_playbook_object(paths=["starttaskid"], values=["0"])
    playbook.tasks = {
        "0": {
            "id": "test task",
            "type": "regular",
            "message": {"replyOptions": ["yes"]},
            "nexttasks": {"#none#": "1"},
        },
        "1": {
            "id": "test task",
            "type": "condition",
            "message": {"replyOptions": ["yes"]},
            "nexttasks": {"no": ["2"]},
        },
    }
    assert IsPlaybookHasUnconnectedTasks().is_valid([playbook])


def test_is_playbook_has_unconnected_tasks_not_valid():
    """
    Given: A playbook with tasks that are not connected to the root task.
    When: Validating the playbook.
    Then: The playbook is not valid.
    """
    playbook = create_playbook_object(paths=["starttaskid"], values=["0"])
    playbook.tasks = {
        "0": {
            "id": "test task",
            "type": "regular",
            "message": {"replyOptions": ["yes"]},
            "nexttasks": {"#none#": "1"},
        },
        "1": {
            "id": "test task",
            "type": "condition",
            "message": {"replyOptions": ["yes"]},
            "nexttasks": {"no": ["2"]},
        },
        "3": {
            "id": "test task",
            "type": "condition",
            "message": {"replyOptions": ["yes"]},
            "nexttasks": {"no": ["2"]},
        },
    }
    assert not IsPlaybookHasUnconnectedTasks().is_valid([playbook])
