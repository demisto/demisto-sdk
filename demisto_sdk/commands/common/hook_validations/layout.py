from abc import ABC, abstractmethod
from distutils.version import LooseVersion

from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator

FROM_VERSION_LAYOUTS_CONTAINER = '6.0.0'


class LayoutBaseValidator(ContentEntityValidator, ABC):
    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, **kwargs)
        self.from_version = self.current_file.get('fromVersion')
        self.to_version = self.current_file.get('toVersion')

    def is_valid_layout(self, validate_rn=True) -> bool:
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        return (super().is_valid_file(validate_rn) and
                self.is_valid_version() and
                self.is_valid_from_version() and
                self.is_valid_to_version() and
                self.is_to_version_higher_than_from_version())

    def is_valid_version(self) -> bool:
        """Checks if version field is valid. uses default method.

        Returns:
            bool. True if version is valid, else False.
        """
        return self._is_valid_version()

    def is_to_version_higher_than_from_version(self) -> bool:
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

    @abstractmethod
    def is_valid_from_version(self) -> bool:
        pass

    @abstractmethod
    def is_valid_to_version(self) -> bool:
        pass


class LayoutsContainerValidator(LayoutBaseValidator):
    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if LooseVersion(self.from_version) < LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('fromVersion')
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if self.to_version and LooseVersion(self.to_version) < LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('toVersion')
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True


class LayoutValidator(LayoutBaseValidator):

    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if self.from_version:
            if LooseVersion(self.from_version) >= LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
                error_message, error_code = Errors.invalid_version_in_layout('fromVersion')
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    return False
        return True

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if not self.to_version or LooseVersion(self.to_version) >= LooseVersion(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layout('toVersion')
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False
        return True
