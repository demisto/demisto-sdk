import os
from typing import List, Optional

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.validate.validators.base_validator import (
    FixingResult,
    ValidationResult,
)


class ValidationResults:
    def __init__(
        self,
        json_file_path: Optional[str] = None,
        only_throw_warnings: Optional[List[str]] = None,
    ):
        """
            The ValidationResults init method.
        Args:
            json_file_path Optional[str]: The json path to write the outputs into.
            only_throw_warnings (list): The list of error codes to only warn about.
        """
        self.only_throw_warning = only_throw_warnings
        self.results: List[ValidationResult] = []
        self.fixing_results: List[FixingResult] = []
        if json_file_path:
            self.json_file_path = (
                os.path.join(json_file_path, "validate_outputs.json")
                if os.path.isdir(json_file_path)
                else json_file_path
            )
        else:
            self.json_file_path = ""

    def post_results(self) -> int:
        """
            Go through the validation results list,
            posting the warnings / failure message for failed validation,
            and calculates the exit_code.

        Returns:
            int: The exit code number - 1 if the validations failed, otherwise return 0
        """
        exit_code = 0
        if self.json_file_path:
            self.write_validation_results()
        for result in self.results:
            if (
                self.only_throw_warning
                and result.validator.error_code in self.only_throw_warning
            ):
                logger.warning(f"[yellow]{result.format_readable_message}[/yellow]")
            else:
                logger.error(f"[red]{result.format_readable_message}[/red]")
                exit_code = 1
        for fixing_result in self.fixing_results:
            if not self.only_throw_warning or fixing_result.validator.error_code not in self.only_throw_warning:
                exit_code = 1
            logger.warning(f"[yellow]{fixing_result.format_readable_message}[/yellow]")
        if not exit_code:
            logger.info("[green]All validations passed.[/green]")
        return exit_code

    def write_validation_results(self):
        """
        If the json path argument is given,
        Writing all the results into a json file located in the given path.
        """
        json_validations_list = [result.format_json_message for result in self.results]
        json_fixing_list = [
            fixing_result.format_json_message for fixing_result in self.fixing_results
        ]
        results = {
            "validations": json_validations_list,
            "fixed validations": json_fixing_list,
        }

        json_object = json.dumps(results, indent=4)

        # Writing to sample.json
        with open(self.json_file_path, "w") as outfile:
            outfile.write(json_object)

    def append(self, validation_result: ValidationResult):
        """Append an item to the validation results list.

        Args:
            validation_result (ValidationResult): the validation result to append.
        """
        self.results.append(validation_result)

    def append_fixing_results(self, fixing_result: FixingResult):
        """Append an item to the fixing results list.

        Args:
            fixing_result (FixingResult): the fixing result to append.
        """
        self.fixing_results.append(fixing_result)

    def extend(self, validation_results: List[ValidationResult]):
        """Extending the list of ValidationResult objects with a given list of validation results.

        Args:
            validation_results (List[ValidationResult]): The list of ValidationResult objects to add to the existing list.
        """
        self.results.extend(validation_results)

    def extend_fixing_results(self, fixing_results: List[FixingResult]):
        """Extending the list of FixingResult objects with a given list of FixingResult objects.

        Args:
            fixing_results (List[FixingResult]): The list of FixingResult objects to add to the existing list.
        """
        self.fixing_results.extend(fixing_results)
