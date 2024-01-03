import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.tools import (
    collect_all_inputs_from_inputs_section,
    collect_all_inputs_in_use,
)


@pytest.mark.parametrize(
    "content_item, expected_result",
    [
        (
            create_playbook_object(
                paths=["tasks"],
                values=[
                    {"0": {"inputs.hello": "test"}, "1": {"inputs.example": "test"}}
                ],
            ),
            {"hello: test", "example: test"},
        ),
        (
            create_playbook_object(
                paths=["tasks"],
                values=[{"0": {"inputs": "test"}, "1": {"inputs": "test2"}}],
            ),
            set(),
        ),
    ],
)
def test_collect_all_inputs_in_use(content_item, expected_result):
    """
    Given:
        - A playbook with inputs in some tasks
          Case 1:
            The inputs for the first task are 'inputs.hello: test'
            The inputs for the second task are 'inputs.example: test'
          Case 2:
            The inputs for the first task are 'inputs: test'
            The inputs for the second task are 'inputs: test2'
    When:
        - Running collect_all_inputs_in_use
    Then:
        - Return a set of input names and values from any task in the playbook, if the inputs match the pattern inputs.<input_name>
        Case 1: The results should be A set object containing:
            'hello: test'
           'example: test'
        Case 2: The results should be:
            An empty set object. (Because the inputs are not in the pattern inputs.<input_name>)
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
