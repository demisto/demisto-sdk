from typing import List, Set

from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
)
from demisto_sdk.commands.validate.initializer import Initializer
from demisto_sdk.commands.validate.validation_results import (
    ValidationResults,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
)


class ValidateManager:
    def __init__(
        self,
        use_git=False,
        validate_all=False,
        file_path=None,
        config_file_category_to_run=None,
        multiprocessing=True,
        prev_ver=None,
        json_file_path=None,
        staged=False,
        allow_autofix=False,
        config_file_path=None,
        only_committed_files=None,
    ):
        self.validate_all = validate_all
        self.file_path = file_path
        self.staged = staged
        self.run_with_multiprocessing = multiprocessing
        self.allow_autofix = allow_autofix
        self.config_file_path = config_file_path
        self.category_to_run = config_file_category_to_run
        self.json_file_path = json_file_path
        self.validation_results = ValidationResults(json_file_path=self.json_file_path)
        self.config_reader = ConfigReader(
            config_file_path=self.config_file_path,
            category_to_run=self.category_to_run,
        )
        self.initializer = Initializer(
            use_git=use_git,
            staged=self.staged,
            committed_only=only_committed_files,
            prev_ver=prev_ver,
            file_path=self.file_path,
            all_files=self.validate_all,
        )
        self.objects_to_run: Set[BaseContent] = self.initializer.gather_objects_to_run()
        self.use_git = self.initializer.use_git
        self.committed_only = self.initializer.committed_only
        (
            self.validations_to_run,
            self.validations_to_ignore,
            self.warnings,
            self.ignorable_errors,
            self.support_level_dict,
        ) = self.config_reader.gather_validations_to_run(use_git=self.use_git)
        self.validators = self.filter_validators()

    def run_validation(self) -> int:
        """
            Running all the relevant validation on all the filtered files based on the should_run calculations,
            calling the fix method if the validation fail, has an autofix, and the allow_autofix flag is given,
            and calling the post_results at the end.
        Returns:
            int: the exit code to obtained from the calculations of post_results.
        """
        for validator in self.validators:
            for content_object in self.objects_to_run:
                if validator.should_run(
                    content_object, self.ignorable_errors, self.support_level_dict
                ):
                    validation_result = validator.is_valid(content_object)
                    try:
                        if not validation_result.is_valid:
                            self.validation_results.append(validation_result)
                            if self.allow_autofix:
                                validator.fix(content_object)
                    except NotImplementedError:
                        continue

        return self.validation_results.post_results()

    def filter_validators(self) -> List[BaseValidator]:
        """
        Filter the validations by their error code
        according to the validations supported by the given flags according to the config file.

        Returns:
            List[BaseValidator]: the list of the filtered validators
        """
        # gather validator from validate package
        validators = BaseValidator.__subclasses__()
        filtered_validators = []
        for validator in validators:
            run_validation = not self.validations_to_run
            if not run_validation:
                for validation_to_run in self.validations_to_run:
                    if validator.error_code.startswith(validation_to_run):
                        run_validation = True
                        break
            if run_validation:
                for error_to_ignore in self.validations_to_ignore:
                    if validator.error_code.startswith(error_to_ignore):
                        run_validation = False
                        break
                if run_validation:
                    filtered_validators.append(validator)
        return filtered_validators
