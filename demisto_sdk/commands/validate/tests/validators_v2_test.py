from unittest.mock import patch

import pytest
import toml

from demisto_sdk.commands.validate.config_reader import ConfigReader
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
        - Case 4: Make sure the retrieved list contains only the validation with the error_code that actually co-op with the validation_to_run.
    """
    validate_manager = get_validate_manager(mocker)
    validate_manager.validations_to_run = validations_to_run
    with patch.object(BaseValidator, "__subclasses__", return_value=sub_classes):
        results = validate_manager.filter_validators()
        assert results == expected_results
        
@pytest.mark.parametrize(
    "category_to_run, use_git, config_file_content, expected_results",
    [
        (None, True, {"use_git": {"select": ["TE100", "TE101", "TE102"]}}, (["TE100", "TE101", "TE102"], None, None, {})),
        ("custom_category", True, {"custom_category": {"ignorable_errors": ["TE100"], "select": ["TE100", "TE101", "TE102"]}, "use_git": {"select": ["TE105", "TE106", "TE107"]}}, (["TE100", "TE101", "TE102"], None, ["TE100"], {})),
        (None, False, {"validate_all": {"select": ["TE100", "TE101", "TE102"]}}, (["TE100", "TE101", "TE102"], None, None, {})),
        (None, True, {"support_level": {"community": {"ignore": ["TE100", "TE101", "TE102"]}}, "use_git": {"select": ["TE105", "TE106", "TE107"]}}, (["TE105", "TE106", "TE107"], None, None, {"community": {"ignore": ["TE100", "TE101", "TE102"]}})),
    ],
)
def test_gather_validations_to_run(mocker, category_to_run, use_git, config_file_content, expected_results):
    """
    Given
    a category_to_run, a use_git flag, and a config file content.
        - Case 1: No category to run, use_git flag set to True, config file content with only use_git.select section.
        - Case 2: A custom category to run, use_git flag set to True, config file content with use_git.select, and custom_category with both ignorable_errors and select sections.
        - Case 3: No category to run, use_git flag set to False, config file content with validate_all.select section.
        - Case 4: No category to run, use_git flag set to True, config file content with use_git.select, and support_level.community.ignore section.
    When
    - Calling the gather_validations_to_run function.
    Then
        - Case 1: Make sure the retrieved results contains only use_git.select results
        - Case 2: Make sure the retrieved results contains the custom category results and ignored the use_git results.
        - Case 3: Make sure the retrieved results contains the validate_all results.
        - Case 4: Make sure the retrieved results contains both the support level and the use_git sections.
    """
    mocker.patch.object(toml, "load", return_value = config_file_content)
    config_reader = ConfigReader(category_to_run=category_to_run)
    results = config_reader.gather_validations_to_run(use_git=use_git)
    assert results == expected_results
