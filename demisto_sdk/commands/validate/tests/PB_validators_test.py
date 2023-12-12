from demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks import IsInputKeyNotInTasksValidator, ValidationResult
from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object


playbook = create_playbook_object()

def test_is_valid_all_inputs_in_use(playbook, mocker):
    """
    Given:
    - A playbook with all inputs used in tasks

    When:
    - Validating the playbook

    Then:
    - Should return empty list (no errors)
    """
    
    mocker.patch('demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks.collect_all_inputs_in_use', return_value={'input1'})
    mocker.patch('demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks.collect_all_inputs_from_inputs_section', return_value={'input1'})
    result = IsInputKeyNotInTasksValidator().is_valid([playbook])

    assert result == []


def test_is_valid_unused_inputs(playbook, mocker):
    """
    Given:
    - A playbook with unused inputs

    When:
    - Validating the playbook

    Then:
    - Should return ValidationResult for unused inputs
    """
    mocker.patch('demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks.collect_all_inputs_in_use', return_value={'input1'})
    mocker.patch('demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks.collect_all_inputs_from_inputs_section', return_value={'input2'})
    result = IsInputKeyNotInTasksValidator().is_valid([playbook])

    assert len(result) == 1
    assert result[0].message == "The playbook 'path/to/playbook.yml' contains inputs that are not used in any of its tasks: input2"
