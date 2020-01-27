from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator


class ClassifierValidator(BaseValidator):
    def is_valid_version(self):
        """Return if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()
