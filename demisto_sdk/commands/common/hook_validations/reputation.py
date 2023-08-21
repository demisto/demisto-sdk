import re

from packaging.version import Version

from demisto_sdk.commands.common.constants import DEFAULT_CONTENT_ITEM_FROM_VERSION
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)

# Valid indicator type can include letters, numbers whitespaces, ampersands and underscores.
VALID_INDICATOR_TYPE = "^[A-Za-z0-9_& ]*$"


class ReputationValidator(ContentEntityValidator):
    """ReputationValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_file(self, validate_rn=True):
        """Check whether the reputation file is valid or not"""

        is_reputation_valid = all(
            [
                super().is_valid_file(validate_rn),
                self.is_valid_version(),
                self.is_valid_expiration(),
                self.is_required_fields_empty(),
                self.is_valid_indicator_type_id(),
            ]
        )

        # check only on added files
        if not self.old_file:
            is_reputation_valid = all(
                [is_reputation_valid, self.is_id_equals_details()]
            )

        return is_reputation_valid

    @error_codes("RP100")
    def is_valid_version(self) -> bool:
        """Validate that the reputations file as version of -1."""
        is_valid = True

        internal_version = self.current_file.get("version")
        if internal_version != self.DEFAULT_VERSION:
            object_id = self.current_file.get("id")
            error_message, error_code = Errors.wrong_version_reputations(
                object_id, self.DEFAULT_VERSION
            )

            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    @error_codes("RP101")
    def is_valid_expiration(self) -> bool:
        """Validate that the expiration field of a 5.5 reputation file is numeric."""
        from_version = self.current_file.get(
            "fromVersion", DEFAULT_CONTENT_ITEM_FROM_VERSION
        )
        if Version(from_version) >= Version("5.5.0"):
            expiration = self.current_file.get("expiration", "")
            if not isinstance(expiration, int) or expiration < 0:
                (
                    error_message,
                    error_code,
                ) = Errors.reputation_expiration_should_be_numeric()
                if self.handle_error(
                    error_message, error_code, file_path=self.file_path
                ):
                    return False

        return True

    @error_codes("RP104")
    def is_required_fields_empty(self) -> bool:
        """Validate that id and details fields are not empty.
        Returns:
            bool. True if id and details fields are not empty, False otherwise.
        """
        id_ = self.current_file.get("id", None)
        details = self.current_file.get("details", None)
        if not id_ or not details:
            error_message, error_code = Errors.reputation_empty_required_fields()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("RP102")
    def is_id_equals_details(self) -> bool:
        """Validate that the id equal details."""
        id_ = self.current_file.get("id", None)
        details = self.current_file.get("details", None)
        if id_ and details and id_ != details:
            error_message, error_code = Errors.reputation_id_and_details_not_equal()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    @error_codes("RP103")
    def is_valid_indicator_type_id(self) -> bool:
        """Validate that id field is valid.
        Returns:
            bool. True if id field is valid, False otherwise.
        """
        id_ = self.current_file.get("id", None)
        if id_ and not re.match(VALID_INDICATOR_TYPE, id_):
            error_message, error_code = Errors.reputation_invalid_indicator_type_id()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True
