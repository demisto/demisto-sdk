import os
from typing import List, Optional, Set

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate.validators.base_validator import (
    FixResult,
    InvalidContentItemResult,
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
        if json_file_path:
            self.json_file_path = (
                os.path.join(json_file_path, "validate_outputs.json")
                if os.path.isdir(json_file_path)
                else json_file_path
            )
        else:
            self.json_file_path = ""

    def post_results(
        self,
        only_throw_warning: Optional[List[str]] = None,
    ) -> int:
        """
            Go through the validation results list,
            posting the warnings / failure message for failed validation,
            and calculates the exit_code.

        Returns:
            int: The exit code number - 1 if the validations failed, otherwise return 0
        """
        fixed_objects_set: Set[BaseContent] = set()
        exit_code = 0
        if self.json_file_path:
            self.write_results_to_json_file()
        for result in self.validation_results:
            if only_throw_warning and result.validator.error_code in only_throw_warning:
                logger.warning(f"[yellow]{result.format_readable_message}[/yellow]")
            else:
                logger.error(f"[red]{result.format_readable_message}[/red]")
                exit_code = 1
        for fixing_result in self.fixing_results:
            fixed_objects_set.add(fixing_result.content_object)
            if (
                not only_throw_warning
                or fixing_result.validator.error_code not in only_throw_warning
            ):
                exit_code = 1
            logger.warning(f"[yellow]{fixing_result.format_readable_message}[/yellow]")
        for result in self.invalid_content_item_results:
            logger.error(f"[red]{result.format_readable_message}[/red]")
            exit_code = 1
        if not exit_code:
            logger.info("[green]All validations passed.[/green]")
        for fixed_object in fixed_objects_set:
            fixed_object.save()
        return exit_code

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
        invalid_content_item_list = [
            result.format_json_message for result in self.invalid_content_item_results
        ]
        results = {
            "validations": json_validations_list,
            "fixed validations": json_fixing_list,
            "invalid content items": invalid_content_item_list,
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
