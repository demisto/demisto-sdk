import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.tools import (
    collect_all_inputs_from_inputs_section,
    collect_all_inputs_in_use,
    compare_lists,
    is_indicator_pb,
)


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(
                paths=["tasks.0.task.key", "tasks.1.task.key"],
                values=[{"inputs.hello": "test"}, {"inputs.example": "test"}],
            ),
            {
                "Systems",
                "Comments",
                "Timeout",
                "File",
                "hello: test",
                "example: test",
                "ReportFileType",
            },
        ),
        (
            create_playbook_object(
                paths=["tasks.0.task.key", "tasks.1.task.key"],
                values=[{"inputs": "test"}, {"inputs": "test2"}],
            ),
            {"Systems", "File", "ReportFileType", "Timeout", "Comments"},
        ),
    ],
)
def test_collect_all_inputs_in_use(content_item, expected_result):
    """
    Given:
        - A playbook with inputs in certain tasks
          Case 1:
            The first task input is: 'inputs.hello: test'
            The second task input is: 'inputs.example: test'
          Case 2:
            The first task input is: 'inputs: test'
            The second task input is: 'inputs: test2'
    When:
        - Running collect_all_inputs_in_use
    Then:
        - It should return a set of input names and values from any task in the playbook, provided the inputs match the pattern: inputs.<input_name>
        Case 1: The output should be a set object containing all default task inputs and the newly added inputs:
            'hello: test'
            'example: test'
        Case 2: The output should be: Only the default inputs, as the inputs do not match the pattern inputs.<input_name>)
    """
    assert collect_all_inputs_in_use(content_item) == expected_result


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(
                paths=["inputs"],
                values=[
                    [
                        {"key": "inputs.test1", "testing text": "text"},
                        {"key": "inputs.test1", "testing text": "text"},
                    ]
                ],
            ),
            {"inputs.test1"},
        ),
        (
            create_playbook_object(
                paths=["inputs"],
                values=[[{"key": "inputs.test2     ", "testing text": "text"}]],
            ),
            {"inputs.test2"},
        ),
    ],
)
def test_collect_all_inputs_from_inputs_section(content_item, expected_result):
    """
    Given:
        - A playbook with inputs defined in the inputs section
        Case 1: both inputs have the same name and value
        Case 2: the input has a space in the name
    When:
        - Running collect_all_inputs_from_inputs_section.
    Then:
        - A set with all inputs defined in the inputs section with no duplicates or empty spaces are returned.
    """
    assert collect_all_inputs_from_inputs_section(content_item) == expected_result


def test_compare_lists():
    """
    Given:
        - A `main_list` containing the elements "a", "b", and "c".
        - A `sub_list` containing the elements "a", "b", "b", and "d".

    When:
        - The function `compare_lists` is called with `sub_list` and `main_list` as arguments.

    Then:
        - Ensuring the value returned is a list containing the elements "b" and "d", which are present in `sub_list` but not in `main_list`.
    """
    main_list = ["a", "b", "c"]
    sub_list = ["a", "b", "b", "d"]
    assert compare_lists(sub_list, main_list) == [
        "b",
        "d",
    ]


def test_is_indicator_pb_positive_case():
    """
    Given:
        - A playbook with indicators as input query.
    When:
        - Running is_indicator_pb
    Then:
        - It should return True.
    """
    playbook = create_playbook_object(
        ["inputs"],
        [
            [
                {
                    "value": {},
                    "required": False,
                    "description": "",
                    "playbookInputQuery": {"query": "", "queryEntity": "indicators"},
                }
            ],
        ],
    )
    assert is_indicator_pb(playbook)


def test_is_indicator_pb_negative_case():
    """
    Given:
        - A playbook with indicators as input query.
    When:
        - Running is_indicator_pb
    Then:
        - It should return True.
    """
    playbook = create_playbook_object()
    assert not is_indicator_pb(playbook)
