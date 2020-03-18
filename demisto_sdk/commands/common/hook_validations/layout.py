from demisto_sdk.commands.common.constants import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.commands.common.tools import print_error


class LayoutValidator(BaseValidator):

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
            print_error(Errors.wrong_version(self.file_path, self.DEFAULT_VERSION))
            return False
        return True
