import pytest

from demisto_sdk.commands.validate.config_reader import ConfiguredValidations
from demisto_sdk.scripts.validate_validation_config_file import (
    validate_all_configured_error_codes_exist,
    validate_all_validations_run_on_git_mode,
    validate_error_code_not_configured_twice,
)


@pytest.mark.parametrize(
    "configured_validations, expected_exit_code, expected_error_codes_per_msg",
    [
        (
            ConfiguredValidations(
                selected_path_based_section=["PA100", "PA101"],
                selected_use_git_section=["GR100", "GR101"],
                warning_path_based_section=["WA100", "WA101"],
                warning_use_git_section=["GR102", "GR103"],
                ignorable_errors=["GR100", "GR102"],
            ),
            1,
            ["WA100", "WA101"],
        ),
        (
            ConfiguredValidations(
                selected_path_based_section=["PA100", "PA101"],
                selected_use_git_section=["GR100", "GR101"],
                warning_path_based_section=["BA100", "BA101"],
                warning_use_git_section=["GR102", "GR103"],
                ignorable_errors=["GR100", "GR102"],
            ),
            0,
            [],
        ),
    ],
)
def test_validate_all_configured_error_codes_exist(
    caplog,
    configured_validations,
    expected_exit_code,
    expected_error_codes_per_msg,
):
    """
    Given: ConfiguredValidations mock
    - case 1: ConfiguredValidations contains invalid error codes.
    - case 2: ConfiguredValidations contains only valid error codes.
    When: Running validate_all_configured_error_codes_exist.
    Then: Ensure the length of the results is as expected
    - Case 1: should throw an error.
    - Case 2: should pass the validation.
    """
    errors = caplog.records
    exit_code = validate_all_configured_error_codes_exist(configured_validations)
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
    - case 1: No correlation between use_git and path_based sections.
    - case 2: use_git contains path_based section.
    - case 3: Some path_based error codes appears in use_git, but not all.
    When: Running validate_all_validations_run_on_git_mode.
    Then: Ensure the length of the results is as expected
    - Case 1: should throw an error.
    - Case 2: should pass the validation.
    - Case 3: should throw an error.
    """
    exit_code = validate_all_validations_run_on_git_mode(configured_validations)
    errors = caplog.records
    assert exit_code == expected_exit_code
    for expected_error_code_per_msg in expected_error_codes_per_msg:
        assert expected_error_code_per_msg in errors[0].msg


@pytest.mark.parametrize(
    "configured_validations, expected_exit_code, expected_number_of_errors, expected_error_codes_per_msg",
    [
        (
            ConfiguredValidations(
                selected_use_git_section=["GR100", "GR101"],
                selected_path_based_section=["PA100", "PA101"],
                warning_use_git_section=["GR100", "GR101"],
                warning_path_based_section=["PA100", "PA102"],
            ),
            1,
            2,
            [
                ["GR100", "GR101"],
                ["PA100"],
            ],
        ),
        (
            ConfiguredValidations(
                selected_path_based_section=["PA102", "PA103"],
                selected_use_git_section=["PA100", "PA101", "GR100", "GR101"],
                warning_path_based_section=["PA100", "PA101"],
                warning_use_git_section=["GR100", "GR101"],
            ),
            1,
            1,
            [["GR100", "GR101"]],
        ),
        (
            ConfiguredValidations(
                selected_path_based_section=["PA100", "PA101"],
                selected_use_git_section=["PA101", "GR100", "GR101"],
                warning_path_based_section=["PA100", "PA102"],
                warning_use_git_section=["GR108", "GR107"],
            ),
            1,
            1,
            [["PA100"]],
        ),
        (
            ConfiguredValidations(
                selected_path_based_section=["PA100", "PA101"],
                selected_use_git_section=["PA101", "GR100", "GR101"],
                warning_path_based_section=["PA105", "PA106"],
                warning_use_git_section=["GR108", "GR107"],
            ),
            0,
            0,
            [],
        ),
    ],
)
def test_validate_error_code_not_configured_twice(
    caplog,
    configured_validations,
    expected_exit_code,
    expected_number_of_errors,
    expected_error_codes_per_msg,
):
    """
    Given: ConfiguredValidations mock
    - case 1: correlation between the use_git sections and the path_based sections.
    - case 2: correlation only between the use_git sections.
    - case 3: correlation only between the path_based sections.
    - case 4: No correlation for both sections.
    When: Running validate_error_code_not_configured_twice.
    Then: Ensure the length of the results and the error msgs are as expected
    - Case 1: should fail both sections.
    - Case 2: should fail only path_based section.
    - Case 3: should fail only use_git section.
    - Case 4: should pass.
    """
    errors = caplog.records
    exit_code = validate_error_code_not_configured_twice(configured_validations)
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


def test_validate_all_error_codes_configured():
    pass
