import pytest
from demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks import IsInputKeyNotInTasksValidator, ValidationResult
from demisto_sdk.commands.common.git_tools import git_status
from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.playbook import Playbook


@pytest.fixture
def validator():
    """Fixture to create validator instance"""
    return IsInputKeyNotInTasksValidator()


@pytest.fixture
def playbook(mocker):
    """Fixture to create playbook instance"""
    playbook = Playbook('path/to/playbook.yml')
    mocker.patch.object(playbook, 'data', {'inputs': [{'key': 'input1'}, {'key': 'input2'}]}, name= "test")
    return playbook


def test_is_valid_all_inputs_in_use(validator, playbook, mocker):
    """
    Given:
    - A playbook with all inputs used in tasks

    When:
    - Validating the playbook

    Then:
    - Should return empty list (no errors)
    """
    mocker.patch.object(validator, 'collect_all_inputs_in_use', return_value={'input1', 'input2'})

    result = validator.is_valid([playbook])

    assert result == []


def test_is_valid_unused_inputs(validator, playbook, mocker):
    """
    Given:
    - A playbook with unused inputs

    When:
    - Validating the playbook

    Then:
    - Should return ValidationResult for unused inputs
    """
    mocker.patch.object(validator, 'collect_all_inputs_in_use', return_value={'input1'})

    result = validator.is_valid([playbook])

    assert len(result) == 1
    assert result[0].message == "The playbook 'path/to/playbook.yml' contains inputs that are not used in any of its tasks: input2"
