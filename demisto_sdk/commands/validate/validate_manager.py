from pathlib import Path
from typing import List, Optional, Set

from demisto_sdk.commands.common.constants import ExecutionMode
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
    ConfiguredValidations,
)
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.validation_results import (
    ResultWriter,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    InvalidContentItemResult,
    ValidationCaughtExceptionResult,
    ValidationResult,
    get_all_validators,
)


class ValidateManager:
    def __init__(
        self,
        validation_results: ResultWriter,
        config_reader: ConfigReader,
        initializer: Initializer,
        file_path=None,
        allow_autofix=False,
        ignore_support_level=False,
        ignore: Optional[List[str]] = None,
    ):
        self.ignore_support_level = ignore_support_level
        self.file_path = file_path
        self.allow_autofix = allow_autofix
        self.validation_results = validation_results
        self.config_reader = config_reader
        self.initializer = initializer
        self.objects_to_run: Set[BaseContent] = set()
        self.invalid_items: Set[Path] = set()
        (
            self.objects_to_run,
            self.invalid_items,
        ) = self.initializer.gather_objects_to_run_on()
        self.committed_only = self.initializer.committed_only
        self.configured_validations: ConfiguredValidations = self.config_reader.read(
            ignore_support_level=ignore_support_level,
            mode=self.initializer.execution_mode,
            codes_to_ignore=ignore,
        )
        self.validators = self.filter_validators()

    def run_validations(self) -> int:
        """
            Running all the relevant validation on all the filtered files based on the should_run calculations,
            calling the fix method if the validation fail, has an autofix, and the allow_autofix flag is given,
            and calling the post_results at the end.
        Returns:
            int: the exit code to obtained from the calculations of post_results.
        """
        logger.info("Starting validate items.")
        for validator in self.validators:
            logger.debug(f"Starting execution for {validator.error_code} validator.")
            if filtered_content_objects_for_validator := list(
                filter(
                    lambda content_object: validator.should_run(
                        content_item=content_object,
                        ignorable_errors=self.configured_validations.ignorable_errors,
                        support_level_dict=self.configured_validations.support_level_dict,
                        running_execution_mode=self.initializer.execution_mode,
                    ),
                    self.objects_to_run,
                )
            ):
                validation_results: List[ValidationResult] = (
                    validator.obtain_invalid_content_items(
                        filtered_content_objects_for_validator
                    )
                )  # type: ignore
                if (
                    validator.expected_execution_mode == [ExecutionMode.ALL_FILES]
                    and self.initializer.execution_mode == ExecutionMode.ALL_FILES
                ):
                    validation_results = [
                        validation_result
                        for validation_result in validation_results
                        if validation_result.content_object
                        in filtered_content_objects_for_validator
                    ]
                try:
                    if self.allow_autofix and validator.is_auto_fixable:
                        for validation_result in validation_results:
                            try:
                                self.validation_results.append_fix_results(
                                    validator.fix(validation_result.content_object)  # type: ignore
                                )
                            except Exception:
                                logger.error(
                                    f"Could not fix {validation_result.validator.error_code} error for content item {str(validation_result.content_object.path)}"
                                )
                                self.validation_results.append_validation_results(
                                    validation_result
                                )
                    else:
                        self.validation_results.extend_validation_results(
                            validation_results
                        )
                except Exception as e:
                    validation_caught_exception_result = ValidationCaughtExceptionResult(
                        message=f"Encountered an error when validating {validator.error_code} validator: {e}"
                    )
                    self.validation_results.append_validation_caught_exception_results(
                        validation_caught_exception_result
                    )
        if BaseValidator.graph_interface:
            logger.info("Closing graph.")
            BaseValidator.graph_interface.close()
        self.add_invalid_content_items()
        return self.validation_results.post_results(
            config_file_content=self.configured_validations
        )

    def filter_validators(self) -> List[BaseValidator]:
        """
        Filter the validations by their error code
        according to the validations supported by the given flags according to the config file.

        Returns:
            List[BaseValidator]: the list of the filtered validators
        """
        return [
            validator
            for validator in get_all_validators()
            if validator.error_code in self.configured_validations.select
        ]

    def add_invalid_content_items(self):
        """Create results for all the invalid_content_items.

        Args:
        """
        self.validation_results.extend_invalid_content_item_results(
            [
                InvalidContentItemResult(
                    path=invalid_path,
                    message="The given file is not supported in the validate command, please refer to the error above.\n"
                    "The validate command supports: Integrations, Scripts, Playbooks, "
                    "Incident fields, Incident types, Indicator fields, Indicator types, Objects fields, Object types,"
                    " Object modules, Images, Release notes, Layouts, Jobs, Wizards, Descriptions And Modeling Rules.\n"
                    "To fix this issue, please try to run `demisto-sdk format` on the file.",
                    error_code="BA102",
                )
                for invalid_path in self.invalid_items
            ]
        )
