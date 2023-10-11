from pathlib import Path

from demisto_sdk.commands.common.constants import DEMISTO_GIT_UPSTREAM
from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.validate.config_reader import (
    ConfigReader,
)
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
        is_external_repo=False,
        prev_ver=None,
        json_file_path=None,
        only_committed_files=False,
        staged=False,
        debug_git=False,
        include_untracked=False,
        allow_autofix=False,
        config_file_path=None,
    ):
        self.config_reader = ConfigReader(
            config_file_path=config_file_path,
            category_to_run=config_file_category_to_run,
        )
        self.objects_to_run = self.gather_objects_to_run(
            file_path, use_git, validate_all
        )
        self.allow_autofix = allow_autofix
        (
            self.validations_to_run,
            self.validations_to_ignore,
            self.warnings,
            self.ignorable_errors,
            self.support_level_dict,
        ) = self.config_reader.gather_validations_to_run(use_git=use_git)
        self.validators = self.filter_validators()
        self.is_circle = only_committed_files
        self.validate_all = validate_all
        self.use_git = use_git
        self.staged = staged
        self.debug_git = debug_git
        self.include_untracked = include_untracked
        self.run_with_multiprocessing = multiprocessing
        self.is_external_repo = is_external_repo
        self.validation_results = ValidationResults(json_file_path=json_file_path)

        if prev_ver and not prev_ver.startswith(DEMISTO_GIT_UPSTREAM):
            self.prev_ver = self.setup_prev_ver(f"{DEMISTO_GIT_UPSTREAM}/" + prev_ver)
        else:
            self.prev_ver = self.setup_prev_ver(prev_ver)

    def run_validation(self):
        for validator in self.validators:
            for content_object in self.objects_to_run:
                if validator.should_run(
                    content_object, self.ignorable_errors, self.support_level_dict
                ):
                    validation_result = validator.is_valid(content_object)
                    try:
                        if not validation_result.is_valid:
                            self.validation_results.results.append(validation_result)
                            validator.fix(content_object)
                    except NotImplementedError:
                        continue

        return self.validation_results.post_results(self.warnings)

    def gather_objects_to_run(self, file_paths, use_git, validate_all):
        content_objects_to_run = set()
        if use_git:
            file_paths = GitUtil()._get_all_changed_files()
        elif file_paths:
            for file_path in file_paths:
                content_object = BaseContent.from_path(Path(file_path))
                if content_object is None:
                    raise Exception(f"no content found in {file_path}")
                content_objects_to_run.add(content_object)
        if validate_all:
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
