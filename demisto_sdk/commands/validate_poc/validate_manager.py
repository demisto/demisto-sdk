from pathlib import Path
from typing import List

import toml

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.repository import ContentDTO
from demisto_sdk.commands.validate_poc.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)
from demisto_sdk.commands.validate_poc.validators.id_name_validator import *
from demisto_sdk.commands.validate_poc.validators.validation_results import post_results


class ValidateManager:
    def __init__(
        self,
        use_git=False,
        validate_all=False,
        file_path=None,
        config_file_category_to_run=None
    ):
        self.config: dict = toml.load("/Users/yhayun/dev/demisto/demisto-sdk/demisto_sdk/commands/validate_poc/validation_conf.toml")
        self.objects_to_run = self.gather_objects_to_run(file_path, use_git, validate_all)
        self.gather_validations_to_run(use_git, config_file_category_to_run)
        self.validators = self.filter_validators()

    def run(self):
        results: List[ValidationResult] = []

        for validator in self.validators:
            for content_object in self.objects_to_run:
                if validator.should_run(content_object, self.ignorable_errors, self.support_level_dict):
                    validation_result = validator.is_valid(content_object)
                    try:
                        if not validation_result.is_valid:
                            results.append(validation_result)
                            validator.fix(content_object)
                    except NotImplementedError:
                        continue
                            
        return post_results(results, self.warnings)

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
    

    def gather_validations_to_run(self, use_git, config_file_category_to_run):
        flag = config_file_category_to_run or "use_git" if use_git else "validate_all"
        section = self.config.get(flag, {})
        self.validations_to_run = section.get("select")
        self.validations_to_ignore = section.get("ignore")
        self.warnings = section.get("warning")
        self.ignorable_errors = section.get("ignorable_errors")
        self.support_level_dict = self.config.get("support_level", {})


    def filter_validators(self):
        # gather validator from validate_poc package
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
