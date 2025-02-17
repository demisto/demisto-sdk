from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.logger import logger, logging_setup
import typer

from demisto_sdk.commands.validate.config_reader import ConfigReader, ConfiguredValidations
from demisto_sdk.commands.validate.validators.base_validator import get_all_validators

main = typer.Typer()

def validate_all_configured_error_codes_exist(configured_validations: ConfiguredValidations) -> int:
    """
    test that the set of configured validation errors in sdk_validation_config.toml is equal to the set of all existing validation to ensure we don't misconfigure non-existing validations.
    """
    exit_code = 0
    configured_errors_set: Set[str] = set()
    for section in (
        configured_validations.selected_path_based_section,
        configured_validations.selected_use_git_section,
        configured_validations.warning_path_based_section,
        configured_validations.warning_use_git_section,
        configured_validations.ignorable_errors,
    ):
        configured_errors_set = configured_errors_set.union(set(section))
    existing_error_codes: Set[str] = set(
        [validator.error_code for validator in get_all_validators()]
    )
    if (
        configured_non_existing_error_codes := configured_errors_set
        - existing_error_codes
    ):
        logger.error(
                f"[VA100] The following error codes are configured in the config file but a validation co-oping with the error code cannot be found: {','.join(configured_non_existing_error_codes)}."
            )
        exit_code = 1
    return exit_code

def validate_all_validations_run_on_git_mode(configured_validations: ConfiguredValidations) -> int:
    """
    Validate that all validations configured in the path_based section are also configured in the use_git section.
    """
    exit_code = 0
    if non_configured_use_git_error_codes := set(
        configured_validations.selected_path_based_section
    ) - set(configured_validations.selected_use_git_section):
        logger.error(f"[VA101] The following error codes are configured to run on path-based inputs but are not configured to run on git mode: {','.join(non_configured_use_git_error_codes)}.")
        exit_code = 1
    return exit_code

def validate_error_code_not_configured_twice(configured_validations: ConfiguredValidations) -> int:
    """
    validate that no error code is configured both for warning and select in the same section in the config file.
    """
    exit_code = 0
    intersected_use_git_error_codes = set(
        configured_validations.selected_use_git_section
    ) & set(configured_validations.warning_use_git_section)
    intersected_path_based_error_codes = set(
        configured_validations.selected_path_based_section
    ) & set(configured_validations.warning_path_based_section)
    for intersected_error_codes, section in [
            (intersected_use_git_error_codes, "use_git"),
            (intersected_path_based_error_codes, "path_based"),
        ]:
        if intersected_error_codes:
            logger.error(f"[VA102] The following error codes are configured twice in the {section} both under select & warning: {', '.join(intersected_error_codes)}.")
            exit_code = 1
    return exit_code

@main.command()
def validate_config_file(
    config_path: Path = typer.Option(None, help="Path for a config file to run."),
    validations_to_run: List[str] = typer.Option([], help="A list of specific error codes to run on the config file."),
    ) -> None:
    """
    Pre-commit hook to generate docs for changed commands.
    """
    logging_setup(calling_function=__name__)
    config_reader = ConfigReader(
        path=config_path
    )
    configured_validations = config_reader.read()
    validators = {
        "VA100": validate_all_configured_error_codes_exist,
        "VA101": validate_all_validations_run_on_git_mode,
        "VA102": validate_error_code_not_configured_twice,
    }
    exit_code = 0
    filtered_validators = []
    if validations_to_run:
        for validation_to_run in validations_to_run:
            if validation_to_run in validators:
                filtered_validators.append(validators[validation_to_run])
    else:
        filtered_validators = list(validators.values())
    for validation in filtered_validators:
        validation(configured_validations)
        # main function to validate the validation config file.
    raise typer.Exit(code=exit_code)
