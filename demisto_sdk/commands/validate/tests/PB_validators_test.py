import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks import (
    IsInputKeyNotInTasksValidator,
)


@pytest.mark.parametrize(
    "input_in_task,input_in_section, expected_result",
    [
        ({"first_input":"inputs.input_name1"}, [{"key":"input_name1", "value":"input_value1"}], []),
        ({"first_input":"inputs.input_name1", "second_input": "inputs.input_name2"}, [{"key":"input_name1", "value":"input_value1"}], []),
         ({"first_input":"inputs.input_name1"}, [{"key":"input_name2", "value":"input_value2"}], "The playbook 'Detonate File - JoeSecurity V2' contains the following inputs that are not used in any of its tasks: input_name2")
    ],
)
def test_is_valid_all_inputs_in_use(
  input_in_task, input_in_section, expected_result
):
    """
        Given:
        - A playbook with inputs in some tasks and inputs defined in the inputs section
            Scenario 1: All inputs defined in the inputs section are in use in the playbook
            Scenario 2: All inputs defined in the inputs section are in use in the playbook but not all inputs in use are defined in the inputs section
            Scenario 3: All inputs defined in the inputs section are not in use in the playbook

        When:
        - Validating the playbook

        Then:
        - The results should be as expected:
            Scenario 1: The playbook is valid
            Scenario 2: The playbook is valid since all inputs defined in the inputs section are in use in the playbook
            Scenario 3: The playbook is invalid
    """
    playbook = create_playbook_object(paths=['inputs', 'tasks'],values=[input_in_section, {'a':input_in_task}])
    result = IsInputKeyNotInTasksValidator().is_valid([playbook])

    assert result == expected_result if isinstance(expected_result, list) else result[0].message == expected_result
