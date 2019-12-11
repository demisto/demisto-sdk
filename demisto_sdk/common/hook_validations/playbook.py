from demisto_sdk.common.hook_validations.base_validator import BaseValidator


class PlaybookValidator(BaseValidator):
    """PlaybookValidator is designed to validate the correctness of the file structure we enter to content repo.
    for now we only validate the version of the playbook.
    """

    def is_valid_version(self):
        # type: () -> bool
        return self._is_valid_version()
