"""
This module is designed to validate the correctness of generic definition entities in content.
"""
import logging
import os

from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from demisto_sdk.commands.common.tools import get_files_in_dir


class ModelingRuleValidator(ContentEntityValidator):
    """
    ModelingRuleValidator is designed to validate the correctness of the file structure we enter to content repo.
    """
    def __init__(self, structure_validator, ignored_errors=None, print_as_warnings=False, json_file_path=None):
        super().__init__(structure_validator, ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         json_file_path=json_file_path)

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the modeling rule is valid or not
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

    def is_schema_file_exists(self):
        # Gets the schema.json file from the modeling rule folder
        files_to_check = get_files_in_dir(os.path.dirname(self.file_path), ['json'], False)
        print(files_to_check)
