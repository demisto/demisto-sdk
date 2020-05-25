from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator


class LayoutValidator(ContentEntityValidator):

    def is_valid_layout(self, validate_rn=True):  # type: () -> bool
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        answers = [
            super().is_valid_file(validate_rn),
            self.is_valid_version()
        ]
        return all(answers)

    def is_valid_version(self):
        # type: () -> bool
        """Return if version is valid.

        Returns:
            True if version is valid, else False.
        """
        if self.current_file.get('layout', {}).get('version') != self.DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(self.DEFAULT_VERSION)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True
