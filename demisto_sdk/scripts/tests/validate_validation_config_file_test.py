from unittest.mock import patch

import pytest
import toml

from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
    ConfiguredValidations,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA100_is_valid_version import (
    IsValidVersionValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA101_id_should_equal_name import (
    IDNameValidator,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA113_is_content_item_name_contain_trailing_spaces import (
    IsContentItemNameContainTrailingSpacesValidator,
)
from demisto_sdk.commands.validate.validators.IN_validators.IN112_is_display_contain_beta import (
    IsDisplayContainBetaValidator,
)
from demisto_sdk.scripts.validate_validation_config_file import (
    validate_all_configured_error_codes_exist,
    validate_all_error_codes_configured,
    validate_all_validations_run_on_git_mode,
    validate_error_code_not_configured_twice,
)


@pytest.mark.parametrize(
    "config_file_content, expected_exit_code, expected_error_codes_per_msg",
    [
        (
            {
                "path_based_validations": {
                    "select": ["PA100", "PA101"],
                    "warning": ["WA100", "WA101"],
                },
                "use_git": {
                    "select": ["GR100", "GR101"],
                    "warning": ["GR102", "GR103"],
                },
                "ignorable_errors": ["GR100", "GR102"],
            },
            1,
            ["WA100", "WA101"],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["PA100", "PA101"],
                    "warning": ["BA100", "BA101"],
                },
                "use_git": {
                    "select": ["GR100", "GR101"],
                    "warning": ["GR102", "GR103"],
                },
                "ignorable_errors": ["GR100", "GR102"],
            },
            0,
            [],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["PA100", "PA101"],
                    "warning": ["BA100", "BA101"],
                },
                "use_git": {
                    "select": ["GR100", "GR101"],
                    "warning": ["GR102", "GR103"],
                },
                "ignorable_errors": ["GR100", "GR102"],
                "custom_section": {
                    "select": ["PA100", "PA101"],
                    "warning": ["WA100", "WA101"],
                },
            },
            1,
            ["WA100", "WA101"],
        ),
    ],
)
def test_validate_all_configured_error_codes_exist(
    mocker,
    caplog,
    config_file_content,
    expected_exit_code,
    expected_error_codes_per_msg,
):
    """
    Given: validation config file mock
    - Case 1: validation config file contains invalid error codes.
    - Case 2: validation config file contains only valid error codes.
    - Case 3: validation config file contains a custom section with invalid error codes.
    When: Running validate_all_configured_error_codes_exist.
    Then: Ensure the exit code and the error codes in the error msg are correct.
    - Case 1: should throw an error.
    - Case 2: should pass the validation.
    - Case 3: should throw an error.
    """
    errors = caplog.records
    mocker.patch.object(toml, "load", return_value=config_file_content)
    config_reader = ConfigReader()
    exit_code = validate_all_configured_error_codes_exist(
        ConfiguredValidations(), config_reader.config_file_content
    )
    assert exit_code == expected_exit_code
    for expected_error_code_per_msg in expected_error_codes_per_msg:
        assert expected_error_code_per_msg in errors[0].msg


@pytest.mark.parametrize(
    "configured_validations, expected_exit_code, expected_error_codes_per_msg",
    [
        (
            ConfiguredValidations(
                selected_path_based_section=["PA100", "PA101"],
                selected_use_git_section=["GR100", "GR101"],
            ),
            1,
            ["PA100", "PA101"],
        ),
        (
            ConfiguredValidations(
                selected_path_based_section=["PA100", "PA101"],
                selected_use_git_section=["PA100", "PA101", "GR100", "GR101"],
            ),
            0,
            [],
        ),
        (
            ConfiguredValidations(
                selected_path_based_section=["PA100", "PA101"],
                selected_use_git_section=["PA101", "GR100", "GR101"],
            ),
            1,
            ["PA100"],
        ),
    ],
)
def test_validate_all_validations_run_on_git_mode(
    caplog,
    configured_validations,
    expected_exit_code,
    expected_error_codes_per_msg,
):
    """
    Given: ConfiguredValidations mock
    - Case 1: No correlation between use_git and path_based sections.
    - Case 2: use_git contains path_based section.
    - Case 3: Some path_based error codes appears in use_git, but not all.
    When: Running validate_all_validations_run_on_git_mode.
    Then: Ensure the exit code and the error codes are correct.
    - Case 1: should throw an error.
    - Case 2: should pass the validation.
    - Case 3: should throw an error.
    """
    exit_code = validate_all_validations_run_on_git_mode(configured_validations, {})
    errors = caplog.records
    assert exit_code == expected_exit_code
    for expected_error_code_per_msg in expected_error_codes_per_msg:
        assert expected_error_code_per_msg in errors[0].msg


@pytest.mark.parametrize(
    "config_file_content, expected_exit_code, expected_number_of_errors, expected_error_codes_per_msg",
    [
        (
            {
                "path_based_validations": {
                    "select": ["PA100", "PA101"],
                    "warning": ["PA100", "PA102"],
                },
                "use_git": {
                    "select": ["GR100", "GR101"],
                    "warning": ["GR100", "GR101"],
                },
            },
            1,
            2,
            [
                ["PA100", "path_based_validations"],
                ["GR100", "GR101", "use_git"],
            ],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["PA102", "PA103"],
                    "warning": ["PA100", "PA101"],
                },
                "use_git": {
                    "select": ["PA100", "PA101", "GR100", "GR101"],
                    "warning": ["GR100", "GR101"],
                },
            },
            1,
            1,
            [["GR100", "GR101", "use_git"]],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["PA100", "PA101"],
                    "warning": ["PA100", "PA102"],
                },
                "use_git": {
                    "select": ["PA101", "GR100", "GR101"],
                    "warning": ["GR108", "GR107"],
                },
            },
            1,
            1,
            [["PA100", "path_based_validations"]],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["PA100", "PA101"],
                    "warning": ["PA105", "PA106"],
                },
                "use_git": {
                    "select": ["PA101", "GR100", "GR101"],
                    "warning": ["GR108", "GR107"],
                },
            },
            0,
            0,
            [],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["PA100", "PA101"],
                    "warning": ["PA105", "PA106"],
                },
                "use_git": {
                    "select": ["PA101", "GR100", "GR101"],
                    "warning": ["GR108", "GR107"],
                },
                "custom_section": {
                    "select": ["PA100", "PA101"],
                    "warning": ["PA100", "PA102"],
                },
            },
            1,
            1,
            [["PA100", "custom_section"]],
        ),
    ],
)
def test_validate_error_code_not_configured_twice(
    mocker,
    caplog,
    config_file_content,
    expected_exit_code,
    expected_number_of_errors,
    expected_error_codes_per_msg,
):
    """
    Given: config file content mock
    - Case 1: correlation between the use_git sections and the path_based sections.
    - Case 2: correlation only between the use_git sections.
    - Case 3: correlation only between the path_based sections.
    - Case 4: No correlation for both sections.
    - Case 5: correlation only between the custom sections.
    When: Running validate_error_code_not_configured_twice.
    Then: Ensure the length of the results the exit code, and the error codes and sections in the error msgs are as expected.
    - Case 1: should fail both sections.
    - Case 2: should fail only path_based section.
    - Case 3: should fail only use_git section.
    - Case 4: should pass.
    - Case 5: should fail only custom_section section.
    """
    errors = caplog.records
    mocker.patch.object(toml, "load", return_value=config_file_content)
    config_reader = ConfigReader()
    exit_code = validate_error_code_not_configured_twice(
        ConfiguredValidations(), config_reader.config_file_content
    )
    assert expected_exit_code == exit_code
    assert expected_number_of_errors == len(errors)
    assert all(
        [
            all(
                [
                    expected_error_code_in_msg in error.msg
                    for expected_error_code_in_msg in expected_error_codes_in_msg
                ]
            )
            for error, expected_error_codes_in_msg in zip(
                errors, expected_error_codes_per_msg
            )
        ]
    )


@pytest.mark.parametrize(
    "config_file_content, expected_exit_code, expected_error_codes_per_msg",
    [
        (
            {
                "path_based_validations": {
                    "select": ["BA100", "BA101"],
                    "warning": ["BA100", "BA101"],
                },
                "use_git": {"select": ["IN112"], "warning": []},
            },
            1,
            ["BA113"],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["BA100", "BA101"],
                    "warning": ["BA100", "BA101"],
                },
                "use_git": {"select": ["IN112", "BA113"], "warning": ["IN112"]},
            },
            0,
            [],
        ),
        (
            {
                "path_based_validations": {
                    "select": ["BA100", "BA101"],
                    "warning": ["BA100", "BA101"],
                },
                "use_git": {"select": ["IN112"], "warning": ["IN112"]},
                "custom_category": {"select": ["IN112", "BA113"], "warning": ["IN112"]},
            },
            0,
            [],
        ),
    ],
)
def test_validate_all_error_codes_configured(
    mocker,
    caplog,
    config_file_content,
    expected_exit_code,
    expected_error_codes_per_msg,
):
    """
    Given: config file content mock
    - Case 1: config file content contains only some of the existing error codes.
    - Case 2: config file content contains all existing error codes.
    - Case 3: config file content contains all existing error codes and additional custom category.
    When: Running validate_all_error_codes_configured.
    Then: Ensure the exit code and the error codes in the error msg are correct.
    - Case 1: should fail with exit code 1 and error code BA113.
    - Case 2: should pass the validation.
    - Case 3: should pass the validation.
    """
    errors = caplog.records
    existing_error_codes = [
        IsValidVersionValidator,
        IDNameValidator,
        IsDisplayContainBetaValidator,
        IsContentItemNameContainTrailingSpacesValidator,
    ]
    mocker.patch.object(toml, "load", return_value=config_file_content)
    config_reader = ConfigReader()
    with patch(
        "demisto_sdk.scripts.validate_validation_config_file.get_all_validators",
        return_value=existing_error_codes,
    ):
        exit_code = validate_all_error_codes_configured(
            ConfiguredValidations(), config_reader.config_file_content
        )

    assert expected_exit_code == exit_code
    assert all(
        [
            all(
                [
                    expected_error_code_in_msg in error.msg
                    for expected_error_code_in_msg in expected_error_codes_in_msg
                ]
            )
            for error, expected_error_codes_in_msg in zip(
                errors, expected_error_codes_per_msg
            )
        ]
    )
