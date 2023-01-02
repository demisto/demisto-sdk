"""
This module is designed to validate the correctness of generic field entities in content.
"""
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)

GENERIC_FIELD_GROUP = 4
GENERIC_FIELD_ID_PREFIX = "generic_"


class GenericFieldValidator(ContentEntityValidator):
    """
    GenericFieldValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def is_valid_file(
        self, validate_rn=True, is_new_file=False, use_git=False, is_added_file=False
    ):
        """
        Check whether the generic field is valid or not
        """
        answers = [
            super().is_valid_generic_object_file(),
            self.is_valid_group(),
            self.is_valid_id_prefix(),
        ]

        if is_added_file:
            answers.append(self.is_valid_unsearchable_key())

        return all(answers)

    def is_valid_version(self):
        pass

    @error_codes("GF100")
    def is_valid_group(self) -> bool:
        group = self.current_file.get("group")
        if group == GENERIC_FIELD_GROUP:
            return True

        error_message, error_code = Errors.invalid_generic_field_group_value(
            group, GENERIC_FIELD_GROUP
        )
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False

        return True

    @error_codes("GF101")
    def is_valid_id_prefix(self) -> bool:
        """
        Validate that the field 'id' starts with the generic field id's prefix
        """
        generic_field_id = str(self.current_file.get("id"))
        if generic_field_id.startswith(GENERIC_FIELD_ID_PREFIX):
            return True

        error_message, error_code = Errors.invalid_generic_field_id(
            generic_field_id, GENERIC_FIELD_ID_PREFIX
        )
        if self.handle_error(error_message, error_code, file_path=self.file_path):
            return False

        return True

    @error_codes("GF102")
    def is_valid_unsearchable_key(self) -> bool:
        """Validate that the unsearchable key is set to true
        Returns:
            bool. Whether the file's unsearchable key is set to true.
        """
        generic_field_unsearchable = self.current_file.get("unsearchable", True)
        if generic_field_unsearchable:
            return True
        (
            error_message,
            error_code,
        ) = Errors.unsearchable_key_should_be_true_generic_field()
        if self.handle_error(
            error_message,
            error_code,
            file_path=self.file_path,
            suggested_fix=Errors.suggest_fix(self.file_path),
        ):
            return False
        return True
