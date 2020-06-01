from distutils.version import LooseVersion

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator

FROM_VERSION = '6.0.0'
VALID_TYPE_INCOMING = 'mapping-incoming'
VALID_TYPE_OUTGOING = 'mapping-outgoing'


class MapperValidator(ContentEntityValidator):
    def __init__(self, structure_validator, ignored_errors=None,
                 print_as_warnings=False):
        super().__init__(structure_validator, ignored_errors=ignored_errors, print_as_warnings=print_as_warnings)
        self.from_version = ''
        self.to_version = ''

    def is_valid_mapper(self, validate_rn=True):
        """Checks whether the mapper is valid or not.

        Returns:
            bool. True if mapper is valid, else False.
        """
        return all([
            super().is_valid_file(validate_rn),
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_from_version(),
            self.is_valid_type()
        ])

    def is_valid_version(self):
        """Checks if version is valid. uses default method.

        Returns:
            True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_valid_from_version(self):
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        from_version = self.current_file.get('fromVersion', '') or self.current_file.get('fromversion')
        if from_version:
            self.from_version = from_version
            if LooseVersion(from_version) < LooseVersion(FROM_VERSION):
                error_message, error_code = Errors.invalid_from_version_in_mapper()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        else:
            error_message, error_code = Errors.missing_from_version_in_mapper()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_valid_to_version(self):
        """Checks if to version is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        to_version = self.current_file.get('toVersion', '') or self.current_file.get('toversion', '')
        if to_version:
            self.to_version = to_version
            if LooseVersion(to_version) < LooseVersion(FROM_VERSION):
                error_message, error_code = Errors.invalid_to_version_in_mapper()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True

    def is_to_version_higher_from_version(self):
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version and self.from_version:
            if LooseVersion(self.to_version) <= LooseVersion(self.from_version):
                error_message, error_code = Errors.from_version_higher_to_version()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True

    def is_valid_type(self):
        """Checks if type field is valid.

        Returns:
            bool. True if type field is valid, else False.
        """
        if self.current_file.get('type') not in [VALID_TYPE_INCOMING, VALID_TYPE_OUTGOING]:
            error_message, error_code = Errors.invalid_type_in_mapper()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True
