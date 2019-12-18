from demisto_sdk.common.hook_validations.base_validator import BaseValidator


class PlaybookValidator(BaseValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo."""

    def is_valid_version(self):  # type: () -> bool
        """Check whether the playbook version is equal to DEFAULT_VERSION (see base_validator class)

        Return:
            bool. whether the version is valid or not
        """
        return self._is_valid_version()

    def is_valid_playbook(self, is_new_playbook=True):  # type: (bool) -> bool
        """Check whether the playbook is valid or not.

         Args:
            is_new_playbook (bool): whether the playbook is new or modified

        Returns:
            bool. Whether the playbook is valid or not
        """

        if is_new_playbook:
            new_playbook_checks = [
                self.is_valid_version(),
                self.is_id_equals_name()
            ]
            answers = all(new_playbook_checks)
        else:
            # for new playbooks - run all playbook checks.
            # for modified playbooks - only validate the version.
            modified_playbook_checks = [
                self.is_valid_version()
            ]
            answers = all(modified_playbook_checks)

        return answers

    def is_id_equals_name(self):  # type: () -> bool
        """Check whether the playbook ID is equal to its name.

        Returns:
            bool. Whether the file id equals to its name
        """
        return super(PlaybookValidator, self)._is_id_equals_name('playbook')
