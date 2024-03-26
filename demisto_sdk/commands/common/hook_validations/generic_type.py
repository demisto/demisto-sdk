"""
This module is designed to validate the correctness of generic type entities in content.
"""

from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)


class GenericTypeValidator(ContentEntityValidator):
    """
    GenericTypeValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the generic type is valid or not
        """
        answers = [super().is_valid_generic_object_file()]

        return all(answers)

    def is_valid_version(self):
        pass
