import pytest
from demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks import IsInputKeyNotInTasksValidator, ValidationResult
from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object


playbook = create_playbook_object()
@pytest.mark.parametrize("input_in_task,input_in_section, expected_result", [
    ({'input1', 'inputs3'}, {'input1'}, []),
    ({'input1', 'inputs3'}, {'input1','input2'}, "The playbook 'Phishing Investigation - Generic' contains the following inputs that are not used in any of its tasks: input2")
])
def test_is_valid_all_inputs_in_use(mocker, input_in_task, input_in_section, expected_result):
    """
    Given:
    - A playbook with inputs in some tasks and inputs defined in the inputs section

    When:
    - Validating the playbook

    Then:
    - If the inputs defined in the inputs section are not all in the playbook, return a list of errors, else return an empty list
,    """
    
    mocker.patch('demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks.collect_all_inputs_in_use', return_value=input_in_task)
    mocker.patch('demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks.collect_all_inputs_from_inputs_section', return_value=input_in_section)
    result = IsInputKeyNotInTasksValidator().is_valid([playbook])
    if input_in_section == {'input2', 'input1'}:
        assert result[0].message == expected_result
    else:
        assert result == expected_result

