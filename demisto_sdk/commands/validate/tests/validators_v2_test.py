import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import toml

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.integration import IntegrationParser
from demisto_sdk.commands.content_graph.tests.test_tools import load_yaml
from demisto_sdk.commands.validate.config_reader import ConfigReader
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.validate_manager_v2 import ValidateManager
from demisto_sdk.commands.validate.validation_results import ValidationResults
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixingResult,
    ValidationResult,
)
from TestSuite.pack import Pack
from TestSuite.test_tools import str_in_call_args_list


def get_validate_manager(mocker):
    mocker.patch.object(Initializer, "gather_objects_to_run", return_value={})
    return ValidateManager()


class ValidatorNoOne(BaseValidator):
    error_code = "TE100"


class ValidatorNoTwo(BaseValidator):
    error_code = "TE101"


class ValidatorNoThree(BaseValidator):
    error_code = "TE102"

parser = IntegrationParser(Path("demisto_sdk/commands/validate/tests/test_data/integration.yml"), list(MarketplaceVersions))
TEST_INTEGRATION = Integration.from_orm(parser)


@pytest.mark.parametrize(
    "validations_to_run, sub_classes, expected_results",
    [
        ([], [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree], []),
        (
            ["TE100", "TE101"],
            [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree],
            [ValidatorNoOne(), ValidatorNoTwo()],
        ),
        (["TE"], [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree], []),
        (
            ["TE100", "TE103"],
            [ValidatorNoOne, ValidatorNoTwo, ValidatorNoThree],
            [ValidatorNoOne()],
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
    "category_to_run, use_git, config_file_content, expected_results, ignore_support_level",
    [
        (
            None,
            True,
            {"use_git": {"select": ["TE100", "TE101", "TE102"]}},
            (["TE100", "TE101", "TE102"], [], [], {}),
            False,
        ),
        (
            "custom_category",
            True,
            {
                "custom_category": {
                    "ignorable_errors": ["TE100"],
                    "select": ["TE100", "TE101", "TE102"],
                },
                "use_git": {"select": ["TE105", "TE106", "TE107"]},
            },
            (["TE100", "TE101", "TE102"], [], ["TE100"], {}),
            False,
        ),
        (
            None,
            False,
            {"validate_all": {"select": ["TE100", "TE101", "TE102"]}},
            (["TE100", "TE101", "TE102"], [], [], {}),
            False,
        ),
        (
            None,
            True,
            {
                "support_level": {"community": {"ignore": ["TE100", "TE101", "TE102"]}},
                "use_git": {"select": ["TE105", "TE106", "TE107"]},
            },
            (
                ["TE105", "TE106", "TE107"],
                [],
                [],
                {"community": {"ignore": ["TE100", "TE101", "TE102"]}},
            ),
            False,
        ),
        (
            None,
            True,
            {
                "support_level": {"community": {"ignore": ["TE100", "TE101", "TE102"]}},
                "use_git": {"select": ["TE105", "TE106", "TE107"]},
            },
            (
                ["TE105", "TE106", "TE107"],
                [],
                [],
                {},
            ),
            True,
        ),
    ],
)
def test_gather_validations_to_run(
    mocker, category_to_run, use_git, config_file_content, expected_results, ignore_support_level
):
    """
    Given
    a category_to_run, a use_git flag, a config file content, and a ignore_support_level flag.
        - Case 1: No category to run, use_git flag set to True, config file content with only use_git.select section, and ignore_support_level set to False.
        - Case 2: A custom category to run, use_git flag set to True, config file content with use_git.select, and custom_category with both ignorable_errors and select sections, and ignore_support_level set to False.
        - Case 3: No category to run, use_git flag set to False, config file content with validate_all.select section, and ignore_support_level set to False.
        - Case 4: No category to run, use_git flag set to True, config file content with use_git.select, and support_level.community.ignore section, and ignore_support_level set to False.
        - Case 5: No category to run, use_git flag set to True, config file content with use_git.select, and support_level.community.ignore section, and ignore_support_level set to True.
    When
    - Calling the gather_validations_to_run function.
    Then
        - Case 1: Make sure the retrieved results contains only use_git.select results
        - Case 2: Make sure the retrieved results contains the custom category results and ignored the use_git results.
        - Case 3: Make sure the retrieved results contains the validate_all results.
        - Case 4: Make sure the retrieved results contains both the support level and the use_git sections.
        - Case 5: Make sure the retrieved results contains only the use_git section.
    """
    mocker.patch.object(toml, "load", return_value=config_file_content)
    config_reader = ConfigReader(category_to_run=category_to_run)
    results = config_reader.gather_validations_to_run(use_git=use_git, ignore_support_level=ignore_support_level)
    assert results == expected_results


@pytest.mark.parametrize(
    "results, fixing_results, expected_results",
    [
        (
            [ValidationResult(validator=ValidatorNoOne(), is_valid=False, message="", content_object=TEST_INTEGRATION, old_content_object=None)], [], {"validations": [{'file path': str(TEST_INTEGRATION.path), 'is_valid': False, 'error code': 'TE100', 'message': ''}], "fixed validations": []},
        ),
        (
            [], [], {"validations": [], "fixed validations": []}
        ),
        (
            [ValidationResult(validator=ValidatorNoOne(), is_valid=False, message="", content_object=TEST_INTEGRATION, old_content_object=None)], [FixingResult(validator=ValidatorNoOne(), message="Fixed this issue", content_object=TEST_INTEGRATION)], {"validations": [{'file path': str(TEST_INTEGRATION.path), 'is_valid': False, 'error code': 'TE100', 'message': ''}], "fixed validations": [{'file path': str(TEST_INTEGRATION.path), 'error code': 'TE100', 'message': 'Fixed this issue'}]}
        ),
    ],
)
def test_write_validation_results(results, fixing_results, expected_results):
    """
    Given
    results and fixing_results lists.
        - Case 1: One validation result.
        - Case 2: Both lists are empty.
        - Case 3: Both lists has one item.
    When
    - Calling the write_validation_results function.
    Then
        - Case 1: Make sure the results hold both list where the fixing results is empty.
        - Case 2: Make sure the results hold both list where both are empty.
        - Case 3: Make sure the results hold both list where both hold 1 result each.
    """
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
        temp_file_path = temp_file.name
        validation_results = ValidationResults(json_file_path=temp_file_path)
        validation_results.results = results
        validation_results.fixing_results = fixing_results
        validation_results.write_validation_results()
        with open(temp_file_path, 'r') as file:
            loaded_data = json.load(file)
            assert loaded_data == expected_results

@pytest.mark.parametrize(
    "only_throw_warnings, results, expected_exit_code, expected_warnings_call_count, expected_error_call_count, expected_error_code_in_warnings, expected_error_code_in_errors",
    [
        (
            ["TE100"], [ValidationResult(validator=ValidatorNoOne(), is_valid=False, message="", content_object=TEST_INTEGRATION)], 0, 1, 0, ["TE100"], []
        ),
        (
            [], [ValidationResult(validator=ValidatorNoOne(), is_valid=False, message="", content_object=TEST_INTEGRATION)], 1, 0, 1, [], ["TE100"]
        ),
        (
            ["TE101"], [ValidationResult(validator=ValidatorNoOne(), is_valid=False, message="", content_object=TEST_INTEGRATION), ValidationResult(validator=ValidatorNoTwo(), is_valid=False, message="", content_object=TEST_INTEGRATION)], 1, 1, 1, ["TE101"], ["TE100"]
        ),
    ],
)
def test_post_results(mocker, only_throw_warnings, results, expected_exit_code, expected_warnings_call_count, expected_error_call_count, expected_error_code_in_warnings, expected_error_code_in_errors):
    """
    Given
    an only_throw_warnings list, and a list of results.
        - Case 1: One failed validation with its error_code in the only_throw_warnings list.
        - Case 2: One failed validation with its error_code not in the only_throw_warnings list.
        - Case 3: One failed validation with its error_code in the only_throw_warnings list and one failed validation with its error_code not in the only_throw_warnings list.
    When
    - Calling the post_results function.
    Then
        - Make sure the error and warning loggers was called the correct number of times with the right error codes, and that the exit code was calculated correctly.
        - Case 1: Make sure the exit_code is 0 (success), and that the warning logger was called once with 'TE100' and the error logger wasn't called.
        - Case 2: Make sure the exit_code is 1 (failure), and that the error logger was called once with 'TE100' and the warning logger wasn't called.
        - Case 3: Make sure the exit_code is 1 (failure), and that the error logger was called once with 'TE100' and the warning logger was called once with 'TE101'
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")
    validation_results = ValidationResults(only_throw_warnings=only_throw_warnings)
    validation_results.results = results
    exit_code = validation_results.post_results()
    assert exit_code == expected_exit_code
    assert logger_warning.call_count == expected_warnings_call_count
    assert logger_error.call_count == expected_error_call_count
    for expected_error_code_in_warning in expected_error_code_in_warnings:
        assert str_in_call_args_list(logger_warning.call_args_list, expected_error_code_in_warning)
    for expected_error_code_in_error in expected_error_code_in_errors:
        assert str_in_call_args_list(logger_error.call_args_list, expected_error_code_in_error)
