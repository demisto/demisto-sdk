"""
This module is designed to validate the correctness of generic definition entities in content.
"""
import json

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
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
        print_as_warnings=False,
        json_file_path=None,
    ):
        super().__init__(
            structure_validator,
            ignored_errors=ignored_errors,
            print_as_warnings=print_as_warnings,
            json_file_path=json_file_path,
        )
        self._is_valid = True

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the triggers file is valid or not
        Note: For now we return True regardless of the item content. More info:
        https://github.com/demisto/etc/issues/48151#issuecomment-1109660727
        """
        self.are_all_fields_exist()

        return self._is_valid

    def is_valid_version(self):
        """
        May deleted or be edited in the future by the use of XSIAM new content
        """
        pass

    @error_codes("LR100")
    def are_all_fields_exist(self):
        """
        Check that all mandatory fields exist in the json file.
        """
        fields_to_check = (
            "rule_id",
            "layout_id",
            "description",
            "rule_name",
            "alerts_filter",
        )
        missing_fields = []
        with open(self.file_path) as sf:
            rule_content = json.load(sf)
            for field in fields_to_check:
                if field not in rule_content.keys():
                    missing_fields.append(field)
        if missing_fields:
            error_message, error_code = Errors.layout_rule_keys_are_missing(
                missing_fields
            )
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False
        return True
