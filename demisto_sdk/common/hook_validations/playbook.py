from demisto_sdk.common.hook_validations.base_validator import BaseValidator


class PlaybookValidator(BaseValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_version(self):
        # type: () -> bool
        return self._is_valid_version()

    def is_valid_playbook(self, is_new_playbook):  # type: (bool) -> bool
        """Check whether the playbook is valid or not"""
        if is_new_playbook:
            new_playbook_checks = [
                self.is_valid_version(),
                self.is_id_equals_name()
            ]
            answers = all(new_playbook_checks)
        else:
            modified_playbook_checks = [
                self.is_valid_version()
            ]
            answers = all(modified_playbook_checks)

        return answers

    def is_id_equals_name(self):
        """Check whether the playbook ID is equal to its name"""
        return super(PlaybookValidator, self)._is_id_equals_name('playbook')
