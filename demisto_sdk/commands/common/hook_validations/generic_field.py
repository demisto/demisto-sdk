"""
This module is designed to validate the correctness of generic field entities in content.
"""
from demisto_sdk.commands.common.constants import GENERIC_FIELD_GROUP, GENERIC_FIELD_ID_PREFIX
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class GenericFieldValidator(ContentEntityValidator):
    """
    GenericFieldValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def is_valid_file(self, validate_rn=True, is_new_file=False, use_git=False):
        """
        Check whether the generic field is valid or not
        """
        answers = [
            super().is_valid_generic_object_file(),
            self.is_valid_group(),
            self.is_valid_id_prefix()
        ]

        return all(answers)

    def is_valid_version(self):
        pass

    def is_valid_group(self):
        # type: () -> bool
        group = self.current_file.get("group")
        if group == GENERIC_FIELD_GROUP:
            return True

        error_message, error_code = Errors.invalid_generic_field_group_value(group)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False

        return True

    def is_valid_id_prefix(self):
        # type: () -> bool
        """
        Validate that the field 'id' starts with the generic field id's prefix
        """
        id = self.current_file.get("id")
        if id.startswith(GENERIC_FIELD_ID_PREFIX):
            return True

        error_message, error_code = Errors.invalid_generic_field_id(id, GENERIC_FIELD_ID_PREFIX)
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False

        return True

