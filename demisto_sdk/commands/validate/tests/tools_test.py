import pytest
from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.validators.tools import (
    collect_all_inputs_from_inputs_section,
    collect_all_inputs_in_use,
)

@pytest.mark.parametrize("input_name, expected_result", [
    ("inputs.hello", {"hello"}),
    ("inputs", {}),
])
def test_collect_all_inputs_in_use(input_name, expected_result):
    """
    Given:
        - A playbook with inputs 
    When:
        - 
    Then:
        - A set of all inputs defined in the 'inputs' section of playbook should be returned
    """
    playbook = create_playbook_object(paths=["name"], values=[input_name])
    assert collect_all_inputs_in_use(playbook) == expected_result


def test_collect_all_inputs_from_inputs_section():
    """
    Given:
        - A playbook with input1 and input2 defined
    When:
        - Running collect_all_inputs_from_inputs_section
    Then:
        - A set with input1 and input2 should be returned
    """
    playbook = create_playbook_object()
    playbook.data["inputs"] =[{"key": "inputs.test     ", "test text": "test"}, {"key": "inputs.test2", "test text": "test"}]

    assert collect_all_inputs_from_inputs_section(playbook) == {'inputs.test2', 'inputs.test'}
