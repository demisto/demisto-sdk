from distutils.version import LooseVersion

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class ReputationValidator(ContentEntityValidator):
    """ReputationValidator is designed to validate the correctness of the file structure we enter to content repo.
    """

    def is_valid_file(self, validate_rn=True):
        """Check whether the reputation file is valid or not
        """

        is_reputation_valid = all([
            super().is_valid_file(validate_rn),
            self.is_valid_version(),
            self.is_valid_expiration()
        ])

        # check only on added files
        if not self.old_file:
            is_reputation_valid = all([
                is_reputation_valid,
                self.is_id_equals_details()
            ])

        return is_reputation_valid

    def is_valid_version(self):
        # type: () -> bool
        """Validate that the reputations file as version of -1."""
        is_valid = True

        internal_version = self.current_file.get('version')
        if internal_version != self.DEFAULT_VERSION:
            object_id = self.current_file.get('id')
            error_message, error_code = Errors.wrong_version_reputations(object_id, self.DEFAULT_VERSION)

            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid

    def is_valid_expiration(self):
        # type: () -> bool
        """Validate that the expiration field of a 5.5 reputation file is numeric."""
        from_version = self.current_file.get("fromVersion", "0.0.0")
        if LooseVersion(from_version) >= LooseVersion("5.5.0"):
            expiration = self.current_file.get('expiration', "")
            if not isinstance(expiration, int) or expiration < 0:
                error_message, error_code = Errors.reputation_expiration_should_be_numeric()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False

        return True

    def is_id_equals_details(self):
        # type: () -> bool
        """Validate that the id equal details."""
        is_valid = True

        id_ = self.current_file.get('id', None)
        details = self.current_file.get('details', None)
        if not id_ or not details or id_ != details:
            error_message, error_code = Errors.reputation_id_and_details_not_equal()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid = False

        return is_valid
