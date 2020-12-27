import os
from abc import ABC, abstractmethod

from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import (
    Layout, LayoutsContainer)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.content_entity_validator import \
    ContentEntityValidator
from packaging.version import Version

FROM_VERSION_LAYOUTS_CONTAINER = '6.0.0'


class LayoutBaseValidator(ContentEntityValidator, ABC):
    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False, layout_container=True,
                 **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, **kwargs)
        self.layout_object = LayoutsContainer(structure_validator.file_path) if layout_container \
            else Layout(structure_validator.file_path)

    def is_valid_layout(self, validate_rn=True) -> bool:
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        return all([super().is_valid_file(validate_rn),
                    self.is_valid_version(),
                    self.is_valid_from_version(),
                    self.is_valid_to_version(),
                    self.is_to_version_higher_than_from_version(),
                    self.is_valid_file_path()
                    ])

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
        if self.layout_object.to_version <= self.layout_object.from_version:
            error_message, error_code = Errors.from_version_higher_to_version()
            if self.handle_error(error_message, error_code, file_path=self.layout_object.path):
                return False
        return True

    @abstractmethod
    def is_valid_from_version(self) -> bool:
        pass

    @abstractmethod
    def is_valid_to_version(self) -> bool:
        pass

    @abstractmethod
    def is_valid_file_path(self) -> bool:
        pass


class LayoutsContainerValidator(LayoutBaseValidator):

    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, layout_container=True, **kwargs)

    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if not self.layout_object.get('fromVersion') or \
                self.layout_object.from_version < Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('fromVersion')
            if self.handle_error(error_message, error_code, file_path=self.layout_object.path):
                return False
        return True

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if self.layout_object.to_version < Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('toVersion')
            if self.handle_error(error_message, error_code, file_path=self.layout_object.path):
                return False
        return True

    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(str(self.layout_object.path))
        if not output_basename.startswith('layoutscontainer-'):
            error_message, error_code = Errors.invalid_file_path_layoutscontainer(output_basename)
            if self.handle_error(error_message, error_code, file_path=self.layout_object.path):
                return False
        return True


class LayoutValidator(LayoutBaseValidator):

    def __init__(self, structure_validator=True, ignored_errors=False, print_as_warnings=False, **kwargs):
        super().__init__(structure_validator, ignored_errors, print_as_warnings, layout_container=False, **kwargs)

    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if self.layout_object.from_version >= Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layout('fromVersion')
            if self.handle_error(error_message, error_code, file_path=self.layout_object.path):
                return False
        return True

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if not self.layout_object.get('toVersion') \
                or self.layout_object.to_version >= Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layout('toVersion')
            if self.handle_error(error_message, error_code, file_path=self.layout_object.path):
                return False
        return True

    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(str(self.layout_object.path))
        if not output_basename.startswith('layout-'):
            error_message, error_code = Errors.invalid_file_path_layout(output_basename)
            if self.handle_error(error_message, error_code, file_path=self.layout_object.path):
                return False
        return True
