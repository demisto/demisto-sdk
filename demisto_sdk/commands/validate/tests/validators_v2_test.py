from unittest.mock import patch

import pytest

from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.validate_manager_v2 import ValidateManager
from demisto_sdk.commands.validate.validators.base_validator import BaseValidator


def get_validate_manager(mocker):
    mocker.patch.object(Initializer, "gather_objects_to_run", return_value={})
    return ValidateManager()


class ValidatorNoOne(BaseValidator):
    error_code = "TE100"


class ValidatorNoTwo(BaseValidator):
    error_code = "TE101"


class ValidatorNoThree(BaseValidator):
    error_code = "TE102"


@pytest.mark.parametrize(
    "validations_to_run, sub_classes, expected_results",
    [
        ([], [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree], []),
        (
            ["TE100", "TE101"],
            [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree],
            [ValidatorNoOne, ValidatorNoTwo],
        ),
        (["TE"], [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree], []),
        (
            ["TE100", "TE103"],
            [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree],
            [ValidatorNoOne],
        ),
    ],
)
def test_filter_validators(mocker, validations_to_run, sub_classes, expected_results):
    """
    Given
    a list of validation_to_run (config file select section mock), and a list of sub_classes (a mock for the BaseValidator sub classes)
        - Case 1: An empty validation_to_run list, and a list of three BaseValidator sub classes.
        - Case 2: A list with 2 validations to run where both validations exist, and a list of three BaseValidator sub classes.
        - Case 3: A list with only 1 item which is a prefix of an existing error code of the validations, and a list of three BaseValidator sub classes.
        - Case 4: A list with two validation to run where only one validation exist, and a list of three BaseValidator sub classes.
    When
    - Calling the filter_validators function.
    Then
        - Case 1: Make sure the retrieved list is empty.
        - Case 2: Make sure the retrieved list contains the two validations co-oping with the two error codes from validation_to_run.
        - Case 3: Make sure the retrieved list is empty.
        - Case 3: Make sure the retrieved list contains only the validation with the error_code that actually co-op with the validation_to_run.
    """
    validate_manager = get_validate_manager(mocker)
    validate_manager.validations_to_run = validations_to_run
    with patch.object(BaseValidator, "__subclasses__", return_value=sub_classes):
        results = validate_manager.filter_validators()
        assert results == expected_results
