import pytest
from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.validators.tools import (
    collect_all_inputs_from_inputs_section,
    collect_all_inputs_in_use,
)


@pytest.mark.parametrize(
    "input_name, expected_result",
    [
        (
            {"0": {"inputs.hello": "test"}, "1": {"inputs.example": "test"}},
            {"hello: test", "example: test"},
        ),
        ({"0": {"inputs": "test"}, "1": {"inputs": "test"}}, set()),
    ],
)
def test_collect_all_inputs_in_use(input_name, expected_result):
    """
    Given:
        - A playbook with inputs in some tasks
    When:
        - Running collect_all_inputs_in_use
    Then:
        - Return a set of input names and values from any task in the playbook, if the inputs match the pattern inputs.<input_name>
        scenario 1: inputs.hello: test
        scenario 2: inputs: test
    """
    playbook = create_playbook_object(paths=["tasks"], values=[input_name])

    assert collect_all_inputs_in_use(playbook) == expected_result


def test_collect_all_inputs_from_inputs_section():
    """
    Given:
        - A playbook with inputs defined in the inputs section
    When:
        - Running collect_all_inputs_from_inputs_section
    Then:
        - A set with all inputs defined in the inputs section with no duplicates or empty spaces are returned.
    """
    playbook = create_playbook_object(
        paths=["inputs"],
        values=[
            [
                {"key": "inputs.test     ", "test text": "test"},
                {"key": "inputs.test", "test text": "test"},
                {"key": "inputs.test2", "test text": "test"},
            ]
        ],
    )

    assert collect_all_inputs_from_inputs_section(playbook) == {
        "inputs.test",
        "inputs.test2",
    }
