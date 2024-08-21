"""
This module is designed to validate the correctness of generic definition entities in content.
"""

import os

from demisto_sdk.commands.common.constants import (
    PARSING_RULE,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.tools import get_files_in_dir


class ParsingRuleValidator(ContentEntityValidator):
    """
    ParsingRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def __init__(
        self,
        structure_validator,
        ignored_errors=None,
        json_file_path=None,
    ):
        super().__init__(
            structure_validator,
            ignored_errors=ignored_errors,
            json_file_path=json_file_path,
        )
        self._is_valid = self.is_valid_rule_suffix(PARSING_RULE)

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the parsing rule is valid or not
        Note: For now we return True regardless of the item content. More info:
        https://github.com/demisto/etc/issues/48151#issuecomment-1109660727
        """
        self.is_files_naming_correct()
        return self._is_valid

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass

    @error_codes("PR100")
    def is_files_naming_correct(self):
        """
        Validates all file naming is as convention.
        """
        files_to_check = get_files_in_dir(
            os.path.dirname(self.file_path), ["yml", "xif"], False
        )
        invalid_files = tuple(
            file
            for file in files_to_check
            if not self.validate_xsiam_content_item_title(file)
        )
        if invalid_files:
            error_message, error_code = Errors.parsing_rules_files_naming_error(
                invalid_files
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False
        return True
