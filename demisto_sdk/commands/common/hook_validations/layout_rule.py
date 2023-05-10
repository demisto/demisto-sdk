"""
This module is designed to validate the correctness of generic definition entities in content.
"""

from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)


class LayoutRuleValidator(ContentEntityValidator):
    """
    LayoutRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
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
        self._is_valid = True

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the triggers file is valid or not
        Note: For now we return True regardless of the item content.
        """

        return True

    def is_valid_version(self) -> bool:
        return True
