from typing import List

import toml

from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate_poc.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class ValidateManager:
    def __init__(
        self,
        use_git=False,
        validate_all=False,
        file_path=None,
    ):
        self.files_to_run = self.gather_files_to_run(file_path, use_git, validate_all)
        self.validation_codes, self.run_using_select = self.gather_validations_to_run(
            use_git, validate_all
        )
        self.config: dict = toml.load("validation_conf.toml")

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
                for content_item in self.files_to_run:
                    if validator.error_code not in content_item.ignored_errors:
                        results.append(validator.is_valid(content_item))
        return self.post_results(results)

    def gather_files_to_run(self, file_path, use_git, validate_all):
        files_to_run = []
        if file_path:
            files_to_run = BaseContent.from_path(file_path)
        elif validate_all:
            files_to_run = BaseContent.from_path("content/Packs")
        elif use_git:
            pass
            # gather all changed files
        else:
            raise Exception("must provide files to run.")
        return self.eliminate_nulls_and_duplications(files_to_run)
    
    def eliminate_nulls_and_duplications(self, files_to_run):
        file_path_list = []
        filtered_list = []
        for file in files_to_run:
            if file and file.path not in file_path_list:
                file_path_list.append(file.path)
                filtered_list.append(file)
        return filtered_list

    def gather_validations_to_run(self, use_git, validate_all):
        flag = "use_git" if use_git else "validate_all"
        if select := self.config.get(flag, {}).get("select"):
            validation_codes, run_using_select = select, True
        else:
            validation_codes, run_using_select = (
                self.config.get(flag, {}).get("ignore"),
                False,
            )
        return validation_codes, run_using_select

    def post_results(self, results: List[ValidationResult] = []):
        only_throw_warning = self.config.get("throw_warnings", {}).get("warnings_list", [])
        is_valid = True
        for result in results:
            if not result.is_valid:
                formatted_error_str = f"{result.file_path}: {result.error_code} - {result.message}"
                if result.error_code in only_throw_warning:
                    logger.warning(f"[yellow]{formatted_error_str}[/yellow]")
                else:
                    logger.error(f"[red]{formatted_error_str}[/red]")
                    is_valid = False
        return is_valid

