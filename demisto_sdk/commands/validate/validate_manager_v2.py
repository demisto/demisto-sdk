from pathlib import Path

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
)
from demisto_sdk.commands.validate.git_initializer import GitInitializer
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
        self.use_git = use_git
        self.file_path = file_path
        self.is_circle = only_committed_files
        self.staged = staged
        self.run_with_multiprocessing = multiprocessing
        self.git_initializer = GitInitializer(
            use_git=use_git, staged=staged, is_circle=self.is_circle
        )
        self.git_initializer.validate_git_installed()
        self.git_initializer.set_prev_ver(prev_ver)
        self.config_reader = ConfigReader(
            config_file_path=config_file_path,
            category_to_run=config_file_category_to_run,
        )
        self.objects_to_run = self.gather_objects_to_run()
        self.allow_autofix = allow_autofix
        (
            self.validations_to_run,
            self.validations_to_ignore,
            self.warnings,
            self.ignorable_errors,
            self.support_level_dict,
        ) = self.config_reader.gather_validations_to_run(use_git=use_git)
        self.validation_results = ValidationResults(
            json_file_path=json_file_path, only_throw_warnings=self.warnings
        )
        self.validators = self.filter_validators()

    def run_validation(self):
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

    def gather_objects_to_run(self):
        """
        Filter the file that should run according to the given flag (-i/-g/-a).

        Returns:
            set: the set of files that should be validated.
        """
        content_objects_to_run = set()
        if self.use_git:
            self.file_path = self.get_files_from_git()
        elif not any([self.file_path, self.validate_all]):
            self.use_git, self.git_initializer.use_git = True, True
            self.is_circle, self.git_initializer.is_circle = True, True
            self.file_path = self.get_files_from_git()
        if self.file_path:
            for file_path in self.file_path:
                content_object = BaseContent.from_path(Path(file_path))
                if content_object is None:
                    raise Exception(f"no content found in {file_path}")
                content_objects_to_run.add(content_object)
        elif self.validate_all:
            content_dto = ContentDTO.from_path(CONTENT_PATH)
            if not isinstance(content_dto, ContentDTO):
                raise Exception("no content found")
            content_objects_to_run = set(content_dto.packs)
        final_content_objects_to_run = set()
        for content_object in content_objects_to_run:
            if isinstance(content_object, Pack):
                for content_item in content_object.content_items:
                    final_content_objects_to_run.add(content_item)
            final_content_objects_to_run.add(content_object)
        return final_content_objects_to_run

    def filter_validators(self):
        """
        Filter the validations by their error code
        according to the validations supported by the given flags according to the config file.

        Returns:
            list: the list of the filtered validators
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

    def get_files_from_git(self):
        self.validation_results.append(self.git_initializer.setup_git_params())
        self.git_initializer.print_git_config()

        (
            modified_files,
            added_files,
            changed_meta_files,
            old_format_files,
            valid_types,
            deleted_files,
        ) = self.git_initializer.collect_files_to_run(self.file_path)
