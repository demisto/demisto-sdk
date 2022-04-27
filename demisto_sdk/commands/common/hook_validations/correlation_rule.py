"""
This module is designed to validate the correctness of generic definition entities in content.
"""
import logging

from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class CorrelationRuleValidator(ContentEntityValidator):
    """
    CorrelationRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the correlation rule is valid or not
        Note: For now we return True regardless of the item content. More info:
        https://github.com/demisto/etc/issues/48151#issuecomment-1109660727
        """
        logging.debug('Automatically considering XSIAM content item as valid, see issue #48151')
        return True

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass
