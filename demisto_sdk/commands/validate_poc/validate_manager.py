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
    ):
        self.config: dict = toml.load("/Users/yhayun/dev/demisto/demisto-sdk/demisto_sdk/commands/validate_poc/validation_conf.toml")
        self.objects_to_run = self.gather_objects_to_run(file_path, use_git, validate_all)
        self.validation_codes, self.run_using_select = self.gather_validations_to_run(
            use_git
        )

    def run(self):
        results: List[ValidationResult] = []
        # gather validator from validate_poc package
        validators = BaseValidator.__subclasses__()

        for validator in validators:
            # if error in validation_codes the left = True if run_using_select = True then we get get True
            # if error in validation_codes the left = True if run_using_select = False then we get get False
            # if error in validation_codes the left = False if run_using_select = True then we get get False
            # if error in validation_codes the left = False if run_using_select = False then we get get True
            if (validator.error_code in self.validation_codes) == self.run_using_select:
                for content_object in self.objects_to_run:
                    if validator.should_run(content_object):
                        validation_result = validator.is_valid(content_object)
                        try:
                            if not validation_result.is_valid:
                                results.append(validation_result)
                                validator.fix(content_object)
                        except NotImplementedError:
                            continue
                            
        return post_results(results, self.config)

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
    

    def gather_validations_to_run(self, use_git):
        flag = "use_git" if use_git else "validate_all"
        if select := self.config.get(flag, {}).get("select"):
            validation_codes, run_using_select = select, True
        else:
            validation_codes, run_using_select = (
                self.config.get(flag, {}).get("ignore"),
                False,
            )
        return validation_codes, run_using_select
