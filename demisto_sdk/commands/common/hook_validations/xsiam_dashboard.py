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


class XSIAMDashboardValidator(ContentEntityValidator):
    """
    XSIAMDashboardValidator is designed to validate the correctness of the file structure we enter to content repo.
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
                FileType.XSIAM_DASHBOARD
            ],
        )
        self._is_valid = True

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the xsiam dashboard is valid or not
        """

        answers = [self.is_files_naming_correct(), super().is_valid_fromversion()]
        return all(answers)

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass

    @error_codes("XD100")
    def is_files_naming_correct(self):
        """
        Validates all file naming is as convention.
        """
        if not self.validate_xsiam_content_item_title(self.file_path):
            error_message, error_code = Errors.xsiam_dashboards_files_naming_error(
                [self.file_path]
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False
        return True
