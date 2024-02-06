import pytest

from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object
from demisto_sdk.commands.validate.validators.PB_validators.PB100_is_no_rolename import (
    IsNoRolenameValidator,
)
from demisto_sdk.commands.validate.validators.PB_validators.PB118_is_input_key_not_in_tasks import (
    IsInputKeyNotInTasksValidator,
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


def test_is_no_rolename_fix():
    """
    Given
        A playbook which has id and an empty rolename.
    When
    - Calling the IsNoRolenameValidator fix function.
    Then
        - Make sure that the rolename was modified correctly, and that the right msg was returned.
    """
    content_item = create_playbook_object(
        paths=["rolename"],
        values=[[]],
    )
    validator = IsNoRolenameValidator()
    assert (
        validator.fix(content_item).message
        == "Removed the 'rolename' from the following playbook 'Detonate File - JoeSecurity V2'."
    )
    assert "rolename" not in content_item.data
