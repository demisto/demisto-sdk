from typing import List, Optional, Set, Tuple

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.commands.update import update_content_graph
from demisto_sdk.commands.content_graph.interface import (
    ContentGraphInterface,
)
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
    ConfiguredValidations,
)
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.validation_results import (
    ValidationResults,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class ValidateManager:
    def __init__(
        self,
        validation_results: ValidationResults,
        config_reader: ConfigReader,
        initializer: Initializer,
        validate_all=False,
        file_path=None,
        multiprocessing=True,
        allow_autofix=False,
        ignore_support_level=False,
    ):
        self.ignore_support_level = ignore_support_level
        self.validate_all = validate_all
        self.file_path = file_path
        self.run_with_multiprocessing = multiprocessing
        self.allow_autofix = allow_autofix
        self.validate_graph = False
        self.validation_results = validation_results
        self.config_reader = config_reader
        self.initializer = initializer
        self.objects_to_run: Set[
            Tuple[BaseContent, Optional[BaseContent]]
        ] = self.initializer.gather_objects_to_run()
        self.use_git = self.initializer.use_git
        self.committed_only = self.initializer.committed_only
        self.configured_validations: ConfiguredValidations = (
            self.config_reader.gather_validations_to_run(
                use_git=self.use_git, ignore_support_level=self.ignore_support_level
            )
        )
        self.validate_graph = False
        self.validators = self.filter_validators()
        if self.validate_graph:
            logger.info("Graph validations were selected, will init graph")
            self.init_graph()

    def run_validations(self) -> int:
        """
            Running all the relevant validation on all the filtered files based on the should_run calculations,
            calling the fix method if the validation fail, has an autofix, and the allow_autofix flag is given,
            and calling the post_results at the end.
        Returns:
            int: the exit code to obtained from the calculations of post_results.
        """
        for validator in self.validators:
            if filtered_content_objects_for_validator := list(
                filter(
                    lambda content_object: validator.should_run(
                        content_object[0],
                        self.configured_validations.ignorable_errors,
                        self.configured_validations.support_level_dict,
                    ),
                    self.objects_to_run,
                )
            ):
                validation_results: List[ValidationResult] = validator.is_valid(*zip(*filtered_content_objects_for_validator))  # type: ignore
                if self.allow_autofix and validator.is_auto_fixable:
                    for validation_result in validation_results:
                        self.validation_results.append_fixing_results(
                            validator.fix(validation_result.content_object)  # type: ignore
                        )
                else:
                    self.validation_results.extend(validation_results)

        return self.validation_results.post_results(only_throw_warning=self.configured_validations.only_throw_warnings)

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
            if validator.error_code in self.configured_validations.validations_to_run:
                validators.append(validator())
                if validator.graph:
                    self.validate_graph = True
        return validators

    def init_graph(self):
        """Initialize and update the graph in case of existing graph validations."""
        graph = ContentGraphInterface()
        update_content_graph(
            graph,
            use_git=True,
            output_path=graph.output_path,
        )
