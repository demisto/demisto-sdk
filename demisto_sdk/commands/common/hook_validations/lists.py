from typing import List

from packaging.version import Version

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import error_codes
from demisto_sdk.commands.common.hook_validations.content_entity_validator import (
    ContentEntityValidator,
)

FROM_VERSION_LISTS = "6.5.0"
DEFAULT_VERSION = -1


class ListsValidator(ContentEntityValidator):
    def __init__(
        self, structure_validator, ignored_errors=False, json_file_path=None, **kwargs
    ):
        super().__init__(structure_validator, ignored_errors, **kwargs)
        self.from_version = self.current_file.get("fromVersion")
        self.to_version = self.current_file.get("toVersion")
        self.version = self.current_file.get("version")

    def is_valid_list(self) -> bool:
        """Check whether the list is valid or not.

        Returns:
            bool. Whether the list is valid or not
        """
        validations: List = [
            self.are_fromversion_and_toversion_in_correct_format(),
            self.are_fromversion_toversion_synchronized(),
            self._is_valid_version(),
            self.is_valid_from_version(),
        ]

        return all(validations)

    def is_valid_version(self) -> bool:
        """Checks if the version field is valid.

        Returns:
            bool. True if version field is valid, else False.
        """
        return self._is_valid_version()

    @error_codes("LI100,LI101")
    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if self.from_version:
            if Version(self.from_version) < Version(FROM_VERSION_LISTS):
                error_message, error_code = Errors.invalid_from_version_in_lists()
                if self.handle_error(
                    error_message,
                    error_code,
                    suggested_fix=Errors.suggest_fix(self.file_path),
                    file_path=self.file_path,
                ):
                    return False
            return True

        error_message, error_code = Errors.missing_from_version_in_list()
        self.handle_error(
            error_message,
            error_code,
            suggested_fix=Errors.suggest_fix(self.file_path),
            file_path=self.file_path,
        )
        return False
