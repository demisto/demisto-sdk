from __future__ import print_function

import os

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import BaseValidator, error_codes


class ReleaseNotesConfigValidator(BaseValidator):
    """Release notes validator is designed to ensure the existence and correctness of the release notes in content repo.

    Attributes:
        rn_config_path (str): the path to the config RN file we are examining at the moment.
    """

    def __init__(self, rn_config_path: str, ignored_errors=None, print_as_warnings=False, suppress_print=False,
                 json_file_path=None, specific_validations=None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path, specific_validations=specific_validations)
        self.rn_config_path = rn_config_path

    def is_file_valid(self) -> bool:
        """
        Checks if given file is valid.
        Return:
            bool. True if file's release notes config are valid, False otherwise.
        """
        validations = [
            self.has_corresponding_rn_file()
        ]

        return all(validations)

    @error_codes('RN110')
    def has_corresponding_rn_file(self) -> bool:
        """
        Checks whether config RN has a corresponding RN file.
        Returns:
            (bool): True if does, false otherwise.
        """
        if not os.path.exists(self.rn_config_path.replace('.json', '.md')):
            error_message, error_code = Errors.release_notes_config_file_missing_release_notes(self.rn_config_path)
            if self.handle_error(error_message, error_code, file_path=self.rn_config_path):
                return False
        return True
