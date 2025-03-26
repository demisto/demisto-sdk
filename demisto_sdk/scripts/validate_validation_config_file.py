import os

os.environ["DEMISTO_SDK_IGNORE_CONTENT_WARNING"] = "True"
from pathlib import Path
from typing import Set

import typer

from demisto_sdk.commands.common.logger import logger, logging_setup
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
    ConfiguredValidations,
)
from demisto_sdk.commands.validate.validators.base_validator import get_all_validators

main = typer.Typer()


def validate_all_configured_error_codes_exist(
    configured_validations: ConfiguredValidations, config_file_content: dict
) -> int:
    """
    Validate that the set of configured validation errors in validation config is equal to the set of all existing validation to ensure we don't misconfigure non-existing validations.

    Arguments:
    - configured_validations (ConfiguredValidations): The ConfiguredValidations object

    Returns:
    - 0 if the validation pass, otherwise return error code.
    """
    exit_code = 0
    configured_errors_set: Set[str] = set()
    for v in config_file_content.values():
        if isinstance(v, dict):
            configured_errors_set = configured_errors_set.union(
                set(v.get("select", []) + v.get("warning", []))
            )

    configured_errors_set = configured_errors_set.union(
        set(configured_validations.ignorable_errors)
    )
    existing_error_codes: Set[str] = set(
        [validator.error_code for validator in get_all_validators()]
    )
    if (
        configured_non_existing_error_codes := configured_errors_set
        - existing_error_codes
    ):
        logger.error(
            f"[VA100] The following error codes are configured in the config file but a validation co-oping with the error code cannot be found: {', '.join(configured_non_existing_error_codes)}."
        )
        exit_code = 1
    return exit_code


def validate_all_validations_run_on_git_mode(
    configured_validations: ConfiguredValidations,
    config_file_content: dict,
) -> int:
    """
    Validate that all validations configured in the path_based section are also configured in the use_git section.

    Arguments:
    - configured_validations (ConfiguredValidations): The ConfiguredValidations object

    Returns:
    - 0 if the validation pass, otherwise return error code.
    """
    exit_code = 0
    if non_configured_use_git_error_codes := set(
        configured_validations.selected_path_based_section
    ) - set(configured_validations.selected_use_git_section):
        logger.error(
            f"[VA101] The following error codes are configured to run on path-based inputs but are not configured to run on git mode: {', '.join(non_configured_use_git_error_codes)}."
        )
        exit_code = 1
    return exit_code


def validate_error_code_not_configured_twice(
    configured_validations: ConfiguredValidations,
    config_file_content: dict,
) -> int:
    """
    validate that no error code is configured both for warning and select in the same section in the config file.

    Arguments:
    - configured_validations (ConfiguredValidations): The ConfiguredValidations object

    Returns:
    - 0 if the validation pass, otherwise return error code.
    """
    exit_code = 0
    for k, v in config_file_content.items():
        if isinstance(v, dict):
            if intersected_error_codes := set(v.get("select", [])) & set(
                v.get("warning", [])
            ):
                exit_code = 1
                logger.error(
                    f"[VA102] The following error codes are configured twice in the {k} both under select & warning: {', '.join(intersected_error_codes)}."
                )
    return exit_code


def validate_all_error_codes_configured(
    configured_validations: ConfiguredValidations,
    config_file_content: dict,
) -> int:
    """
    validate that the set of all validation errors that exist in the new format and the set of all the validation errors configured in the sdk_validation_config are equal to ensure all new validations are being tested.

    Arguments:
    - configured_validations (ConfiguredValidations): The ConfiguredValidations object

    Returns:
    - 0 if the validation pass, otherwise return error code.
    """
    exit_code = 0
    configured_errors_set: Set[str] = set()
    for v in config_file_content.values():
        if isinstance(v, dict):
            configured_errors_set = configured_errors_set.union(
                set(v.get("select", []) + v.get("warning", []))
            )
    existing_error_codes: Set[str] = set(
        [validator.error_code for validator in get_all_validators()]
    )

    if (
        non_configured_existing_error_codes := existing_error_codes
        - configured_errors_set
    ):
        logger.error(
            f"[VA103] The following error codes are not configured in the config file: {', '.join(non_configured_existing_error_codes)}."
        )
        exit_code = 1
    return exit_code


@main.command()
def validate_config_file(
    config_path: Path = typer.Option(..., help="Path for a config file to run."),
    validations_to_run: str = typer.Option(
        "",
        help="A comma separated list of specific error codes to run on the config file.",
    ),
) -> None:
    """
    Pre-commit hook to generate docs for changed commands.
    """
    logging_setup(calling_function=__name__)
    config_reader = ConfigReader(path=config_path)
    configured_validations = config_reader.read()
    config_file_content = config_reader.config_file_content
    validators = {
        "VA100": validate_all_configured_error_codes_exist,
        "VA101": validate_all_validations_run_on_git_mode,
        "VA102": validate_error_code_not_configured_twice,
        "VA103": validate_all_error_codes_configured,
    }
    exit_code = 0
    filtered_validators = []
    if validations_to_run:
        for validation_to_run in validations_to_run.split(","):
            if validation_to_run in validators:
                filtered_validators.append(validators[validation_to_run])
    else:
        filtered_validators = list(validators.values())
    for validation in filtered_validators:
        if validation(configured_validations, config_file_content):
            exit_code = 1
    raise typer.Exit(code=exit_code)
