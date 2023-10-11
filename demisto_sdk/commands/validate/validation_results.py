import os
from typing import List

from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.validate.validators.base_validator import ValidationResult


class ValidationResults:
    def __init__(self, json_file_path):
        self.results: List[ValidationResult] = []
        if json_file_path:
            self.json_file_path = (
                os.path.join(json_file_path, "validate_outputs.json")
                if os.path.isdir(json_file_path)
                else json_file_path
            )
        else:
            self.json_file_path = ""

    def post_results(self, only_throw_warning=[]):
        exit_code = 0
        if self.json_file_path:
            self.write_validation_results()
        for result in self.results:
            if not result.is_valid:
                if result.error_code in only_throw_warning:
                    logger.warning(f"[yellow]{result.format_readable_message}[/yellow]")
                else:
                    logger.error(f"[red]{result.format_readable_message}[/red]")
                    exit_code = 1
        return exit_code
    
    def write_validation_results(self):
        json_validations_list = [result.format_json_message for result in self.results]
        
        json_object = json.dumps(json_validations_list, indent=4)
        
        # Writing to sample.json
        with open(self.json_file_path, "w") as outfile:
            outfile.write(json_object)
