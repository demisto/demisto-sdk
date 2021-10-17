from distutils.version import LooseVersion
from typing import List

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator

FROM_VERSION_LISTS = '6.5.0'


class ListsValidator(ContentEntityValidator):
    def __init__(self, structure_validator, ignored_errors=False, print_as_warnings=False,
                 json_file_path=None, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings,
                         json_file_path=json_file_path, **kwargs)
        self.from_version = self.current_file.get('fromServerVersion')
        self.to_version = self.current_file.get('toServerVersion')

    def is_valid_list(self) -> bool:
        """Check whether the list is valid or not.

        Returns:
            bool. Whether the list is valid or not
        """
        # Lists files have fromServerVersion instead of fromVersion
        validations: List = [
            self.is_valid_version(),
            self.is_valid_from_server_version(),
        ]

        return all(validations)

    def is_valid_version(self) -> bool:
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_valid_from_server_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if self.from_version:
            if LooseVersion(self.from_version) < LooseVersion(FROM_VERSION_LISTS):
                error_message, error_code = Errors.invalid_from_server_version_in_lists('fromServerVersion')
                if self.handle_error(error_message, error_code, suggested_fix=Errors.suggest_fix(self.file_path),
                                     file_path=self.file_path):
                    return False
        return False
