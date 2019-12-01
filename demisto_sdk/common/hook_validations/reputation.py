from demisto_sdk.common.constants import Errors
from demisto_sdk.common.hook_validations.base_validator import BaseValidator
from demisto_sdk.common.tools import print_error


class ReputationValidator(BaseValidator):
    def is_valid_version(self):
        # type: () -> bool
        """Validate that the reputations file as version of -1."""
        is_valid = True
        reputations = self.current_file.get('reputations', [])
        for reputation in reputations:
            internal_version = reputation.get('version')
            if internal_version != self.DEFAULT_VERSION:
                object_id = reputation.get('id')
                print_error(Errors.wrong_version_reputations(self.file_path, object_id, self.DEFAULT_VERSION))
                is_valid = False
                self.is_valid = False
        return is_valid
