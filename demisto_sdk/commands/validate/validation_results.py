import os
from pathlib import Path
from typing import List, Optional, Set, Tuple

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate.config_reader import ConfiguredValidations
from demisto_sdk.commands.validate.validators.base_validator import (
    FixResult,
    InvalidContentItemResult,
    ValidationCaughtExceptionResult,
    ValidationResult,
)


class ResultWriter:
    """
    Handle all the results, this class save all the results during run time and post the results when the whole execution is over.
    The class can either log the results to the terminal or write the results to a json file in a given path.
    The class also calculate the final result for the validations executions based on the validation results and list of errors that need to only the warnings.
    """

    def __init__(
        self,
        json_file_path: Optional[str] = None,
    ):
        """
            The ResultWriter init method.
        Args:
            json_file_path Optional[str]: The json path to write the outputs into.
        """
        self.validation_results: List[ValidationResult] = []
        self.fixing_results: List[FixResult] = []
        self.invalid_content_item_results: List[InvalidContentItemResult] = []
        self.validation_caught_exception_results: List[
            ValidationCaughtExceptionResult
        ] = []
        if json_file_path:
            self.json_file_path = (
                os.path.join(json_file_path, "validate_outputs.json")
                if os.path.isdir(json_file_path)
                else json_file_path
            )
        else:
            self.json_file_path = ""

    def post_validation_results(
        self,
        config_file_content: ConfiguredValidations,
        validation_results: List[ValidationResult],
    ) -> Tuple[int, Set[str], Set[str]]:
        """Summarize the validation results and return the overall exit code and set of failing and warning error codes.

        Args:
            config_file_content (ConfiguredValidations): The ConfiguredValidations object containing the warning level validations.
            validation_results (List[ValidationResult]): The list of ValidationResult objects to summarize.

        Returns:
            Tuple[int, Set[str], Set[str]]: The exit code and sets of failing and warning error codes.
        """
        exit_code = 0
        failing_error_codes: Set[str] = set()
        warning_error_codes: Set[str] = set()
        for result in validation_results:
            if result.validator.error_code in config_file_content.warning:
                warning_error_codes.add(result.validator.error_code)
                logger.warning(f"<yellow>{result.format_readable_message}</yellow>")
            else:
                failing_error_codes.add(result.validator.error_code)
                logger.error(f"<red>{result.format_readable_message}</red>")
                exit_code = 1
        return exit_code, failing_error_codes, warning_error_codes

    def post_results(
        self,
        config_file_content: ConfiguredValidations,
    ) -> int:
        """
            Go through the validation results list,
            posting the warnings / failure message for failed validation,
            and calculates the exit_code.

        Returns:
            int: The exit code number - 1 if the validations failed, otherwise return 0
        """
        fixed_objects_set: Set[BaseContent] = set()
        if self.json_file_path:
            self.write_results_to_json_file()
        exit_code, failing_error_codes, warning_error_codes = (
            self.post_validation_results(config_file_content, self.validation_results)
        )
        for fixing_result in self.fixing_results:
            fixed_objects_set.add(fixing_result.content_object)
            if fixing_result.validator.error_code not in config_file_content.warning:
                exit_code = 1
            logger.warning(f"{fixing_result.format_readable_message}")
        for result in self.invalid_content_item_results:
            logger.error(f"{result.format_readable_message}")
            exit_code = 1
        for result in self.validation_caught_exception_results:
            logger.error(f"{result.format_readable_message}")
            exit_code = 1
        if not exit_code:
            logger.info("<green>All validations passed.</green>")
        self.summarize_validation_results(
            failing_error_codes, warning_error_codes, config_file_content, exit_code
        )
        for fixed_object in fixed_objects_set:
            fixed_object.save()
        return exit_code

    def summarize_validation_results(
        self,
        failing_error_codes: Set[str],
        warning_error_codes: Set[str],
        config_file_content: ConfiguredValidations,
        exit_code: int,
    ):
        """Divide the error codes into groups: warnings, forcemergeable, ignorable, non ignorable, and must-be-handled and post this summary at the end of the execution.

        Args:
            failing_error_codes (Set[str]): The set of failing errors.
            warning_error_codes (Set[str]): The set of warning errors.
            config_file_content (ConfiguredValidations): The ConfiguredValidations object containing the ignorable errors, and path-based sections.
            exit_code (int): The expected exit_code
        """
        forcemergeable_errors = []
        ignorable_errors = []
        must_be_handled_errors = []
        non_ignorable_errors = []
        error_msg: str = ""
        warning_msg: str = ""
        msg: str = "Validate summary\n"
        for failing_error_code in failing_error_codes:
            if failing_error_code in config_file_content.ignorable_errors:
                ignorable_errors.append(failing_error_code)
            else:
                non_ignorable_errors.append(failing_error_code)
            if (
                failing_error_code
                not in config_file_content.selected_path_based_section
            ):
                forcemergeable_errors.append(failing_error_code)
            else:
                must_be_handled_errors.append(failing_error_code)
        if warning_error_codes:
            warning_msg = f"The following errors were reported as warnings: {', '.join(warning_error_codes)}.\n"
            msg = f"{msg}{warning_msg}"
        if ignorable_errors:
            error_msg += (
                f"The following errors can be ignored: {', '.join(ignorable_errors)}.\n"
            )
        if non_ignorable_errors:
            error_msg += f"The following errors cannot be ignored: {', '.join(non_ignorable_errors)}.\n"
        if forcemergeable_errors:
            error_msg += f"The following errors don't run as part of the nightly flow and therefore can be force merged: {', '.join(forcemergeable_errors)}.\n"
        if error_msg:
            msg = f"{msg}The following errors were thrown as a part of this pr: {', '.join(failing_error_codes)}.\n{error_msg}"
        logger.error(f"<red>{msg}</red>")
        if must_be_handled_errors:
            verdict_msg = ""
            verdict_msg += f"###############################################################################################{'#######' * len(must_be_handled_errors)}\n"
            verdict_msg += f"Note that the following errors cannot be force merged and therefore must be handled: {', '.join(must_be_handled_errors)}.\n"
            verdict_msg += f"###############################################################################################{'#######' * len(must_be_handled_errors)}\n"
            logger.error(f"<red>{verdict_msg}</red>")
            msg += "\nnVerdict: PR can be force merged from validate perspective? ❌"
        else:
            verdict_msg = "#############################################################################\n"
            verdict_msg += "Please note that the PR can be force merged from the validation perspective.\n"
            verdict_msg += "############################################################################\n"
            if exit_code:
                logger.warning(f"<green>{verdict_msg}</green>")
            else:
                logger.info(f"<green>{verdict_msg}</green>")
            msg += "\nVerdict: PR can be force merged from validate perspective? ✅"
        self.save_validate_summary_to_artifacts(msg)

    def save_validate_summary_to_artifacts(self, validate_summary: str):
        """Initialize a txt file at with the validate summary.

        Args:
            validate_summary (str): The file name to create.
        """
        if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
            artifacts_folder
        ).exists():
            artifacts_validate_summary_path = Path(
                f"{artifacts_folder}/validate_summary.txt"
            )
            logger.info(
                f"Writing the validate summary results to a txt file at {artifacts_validate_summary_path}."
            )
            with open(artifacts_validate_summary_path, "w") as f:
                f.write(validate_summary)

    def write_results_to_json_file(self):
        """
        If the json path argument is given,
        Writing all the results into a json file located in the given path.
        """
        json_validations_list = [
            result.format_json_message for result in self.validation_results
        ]
        json_fixing_list = [
            fixing_result.format_json_message for fixing_result in self.fixing_results
        ]
        json_invalid_content_item_list = [
            result.format_json_message for result in self.invalid_content_item_results
        ]
        json_validation_caught_exception_list = [
            result.format_json_message
            for result in self.validation_caught_exception_results
        ]
        results = {
            "validations": json_validations_list,
            "fixed validations": json_fixing_list,
            "invalid content items": json_invalid_content_item_list,
            "Validations that caught exceptions": json_validation_caught_exception_list,
        }

        json_object = json.dumps(results, indent=4)

        # Writing to sample.json
        with open(self.json_file_path, "w") as outfile:
            outfile.write(json_object)

    def append_validation_results(self, validation_result: ValidationResult):
        """Append an item to the validation results list.

        Args:
            validation_result (ValidationResult): the validation result to append.
        """
        self.validation_results.append(validation_result)

    def append_fix_results(self, fixing_result: FixResult):
        """Append an item to the fixing results list.

        Args:
            fixing_result (FixResult): the fixing result to append.
        """
        self.fixing_results.append(fixing_result)

    def append_validation_caught_exception_results(
        self, validation_caught_exception_results: ValidationCaughtExceptionResult
    ):
        """Append an item to the validation_caught_exception_results list.

        Args:
            validation_caught_exception_results (ValidationCaughtExceptionResult): the validation_caught_exception result to append.
        """
        self.validation_caught_exception_results.append(
            validation_caught_exception_results
        )

    def extend_validation_results(self, validation_results: List[ValidationResult]):
        """Extending the list of ValidationResult objects with a given list of validation results.

        Args:
            validation_results (List[ValidationResult]): The list of ValidationResult objects to add to the existing list.
        """
        self.validation_results.extend(validation_results)

    def extend_fix_results(self, fixing_results: List[FixResult]):
        """Extending the list of FixResult objects with a given list of FixResult objects.

        Args:
            fixing_results (List[FixResult]): The list of FixResult objects to add to the existing list.
        """
        self.fixing_results.extend(fixing_results)

    def extend_invalid_content_item_results(
        self, invalid_content_item_results: List[InvalidContentItemResult]
    ):
        """Extending the list of InvalidContentItemResult objects with a given list of InvalidContentItemResult objects.

        Args:
            non_content_item_results (List[InvalidContentItemResult]): The List of InvalidContentItemResult objects to add to the existing list.
        """
        self.invalid_content_item_results.extend(invalid_content_item_results)

    def extend_validation_caught_exception_results(
        self, validation_caught_exception_results: List[ValidationCaughtExceptionResult]
    ):
        """Extending the list of ValidationCaughtExceptionResult objects with a given list of ValidationCaughtExceptionResult objects.

        Args:
            non_content_item_results (List[ValidationCaughtExceptionResult]): The List of ValidationCaughtExceptionResult objects to add to the existing list.
        """
        self.validation_caught_exception_results.extend(
            validation_caught_exception_results
        )
