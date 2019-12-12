from demisto_sdk.common.hook_validations.base_validator import BaseValidator


class PlaybookValidator(BaseValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_version(self):
        # type: () -> bool
        return self._is_valid_version()

    def is_valid_playbook(self):  # type: () -> bool
        """Check whether the playbook is valid or not"""
        answers = [
            self.is_valid_version()
        ]
        return all(answers)
