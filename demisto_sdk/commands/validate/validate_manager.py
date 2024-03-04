from pathlib import Path
from typing import List, Set

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import is_abstract_class
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
    ValidationResult,
)


class ValidateManager:
    def __init__(
        self,
        validation_results: ResultWriter,
        config_reader: ConfigReader,
        initializer: Initializer,
        validate_all=False,
        file_path=None,
        allow_autofix=False,
        ignore_support_level=False,
    ):
        self.ignore_support_level = ignore_support_level
        self.validate_all = validate_all
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
        self.use_git = self.initializer.use_git
        self.committed_only = self.initializer.committed_only
        self.configured_validations: ConfiguredValidations = (
            self.config_reader.gather_validations_to_run(
                use_git=self.use_git, ignore_support_level=self.ignore_support_level
            )
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
            if filtered_content_objects_for_validator := list(
                filter(
                    lambda content_object: validator.should_run(
                        content_object,
                        self.configured_validations.ignorable_errors,
                        self.configured_validations.support_level_dict,
                    ),
                    self.objects_to_run,
                )
            ):
                validation_results: List[ValidationResult] = validator.is_valid(filtered_content_objects_for_validator)  # type: ignore
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
        if BaseValidator.graph_interface:
            logger.info("Closing graph.")
            BaseValidator.graph_interface.close()
        self.add_invalid_content_items()
        return self.validation_results.post_results(
            only_throw_warning=self.configured_validations.only_throw_warnings
        )

    def filter_validators(self) -> List[BaseValidator]:
        """
        Filter the validations by their error code
        according to the validations supported by the given flags according to the config file.

        Returns:
            List[BaseValidator]: the list of the filtered validators
        """
        # gather validator from validate package
        validators: List[BaseValidator] = []
        for validator in BaseValidator.__subclasses__():
            if (
                not is_abstract_class(validator)
                and validator.error_code
                in self.configured_validations.validations_to_run
            ):
                validators.append(validator())
        return validators

    def add_invalid_content_items(self):
        """Create results for all the invalid_content_items.

        Args:
        """
        self.validation_results.extend_invalid_content_item_results(
            [
                InvalidContentItemResult(
                    path=invalid_path,
                    message="The given file is not supported in the validate command, see the error above.\n"
                    "The validate command supports: Integrations, Scripts, Playbooks, "
                    "Incident fields, Incident types, Indicator fields, Indicator types, Objects fields, Object types,"
                    " Object modules, Images, Release notes, Layouts, Jobs, Wizards, Descriptions And Modeling Rules.",
                    error_code="BA102",
                )
                for invalid_path in self.invalid_items
            ]
        )
