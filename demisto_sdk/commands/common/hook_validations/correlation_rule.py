"""
This module is designed to validate the correctness of generic definition entities in content.
"""

from demisto_sdk.commands.common.constants import (
    FILETYPE_TO_DEFAULT_FROMVERSION,
    FileType,
)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)
from demisto_sdk.commands.common.logger import logger


class CorrelationRuleValidator(ContentEntityValidator):
    """
    CorrelationRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
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
            oldest_supported_version=FILETYPE_TO_DEFAULT_FROMVERSION[
                FileType.CORRELATION_RULE
            ],
        )

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the correlation rule is valid or not
        """
        logger.debug(
            "Automatically considering XSIAM content item as valid, see issue #48151"
        )

        answers = [
            self.no_leading_hyphen(),
            self.is_files_naming_correct(),
            self.validate_execution_mode_search_window(),
            super().is_valid_fromversion(),
        ]
        return all(answers)

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass

    @error_codes("CR100")
    def no_leading_hyphen(self):
        """

        Returns: False if type of current file is CommentSeq, which means the yaml starts with hyphen, True otherwise.

        """
        if isinstance(self.current_file, list):
            error_message, error_code = Errors.correlation_rule_starts_with_hyphen()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("CR101")
    def is_files_naming_correct(self):
        """
        Validates all file naming is as convention.
        """
        if not self.validate_xsiam_content_item_title(self.file_path):
            error_message, error_code = Errors.correlation_rules_files_naming_error(
                [self.file_path]
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("CR102")
    def validate_execution_mode_search_window(self):
        """
        Validates 'search_window' existence and non-emptiness for 'execution_mode' = 'SCHEDULED'.
        """
        if ("search_window" not in self.current_file) or (
            self.current_file["execution_mode"] == "SCHEDULED"
            and not self.current_file["search_window"]
        ):
            error_message, error_code = Errors.correlation_rules_missing_search_window()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True
