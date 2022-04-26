"""
This module is designed to validate the correctness of generic definition entities in content.
"""

from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class ParsingRuleValidator(ContentEntityValidator):
    """
    ParsingRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the parsing rule is valid or not
        """
        return True

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass
