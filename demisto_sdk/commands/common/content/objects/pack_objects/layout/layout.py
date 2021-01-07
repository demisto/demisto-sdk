import os
from typing import Union

import demisto_client
from demisto_sdk.commands.common.constants import (DEFAULT_VERSION,
                                                   FEATURE_BRANCHES, LAYOUT,
                                                   LAYOUTS_CONTAINER,
                                                   OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from packaging.version import Version
from wcmatch.pathlib import Path

FROM_VERSION_LAYOUTS_CONTAINER = '6.0.0'


class Layout(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, LAYOUT)
        self.base = base if base else BaseValidator()

    def upload(self, client: demisto_client):
        return client.import_layout(file=self.path)

    def validate(self):

        return self.is_valid_layout()

    def is_valid_layout(self) -> bool:
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        return all([
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_than_from_version(),
            self.is_valid_file_path()
        ])

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(self.path)):
                return False
        return True

    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        is_valid = True
        if self.from_version >= Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layout('fromVersion')
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False

        if self.should_run_fromversion_validation() and self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromVersion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False

        return is_valid

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if not self.get('toVersion') \
                or self.to_version >= Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layout('toVersion')
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(str(self.path))
        if not output_basename.startswith('layout-'):
            error_message, error_code = Errors.invalid_file_path_layout(output_basename)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.base.prev_ver or feature_branch_name in self.base.branch_name)
               for feature_branch_name in FEATURE_BRANCHES):
            return False

        return True

    def is_to_version_higher_than_from_version(self) -> bool:
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version <= self.from_version:
            error_message, error_code = Errors.from_version_higher_to_version()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True


class LayoutsContainer(JSONContentObject):
    def __init__(self, path: Union[Path, str], base: BaseValidator = None):
        super().__init__(path, LAYOUTS_CONTAINER)
        self.base = base if base else BaseValidator()

    def upload(self, client: demisto_client):
        """
        Upload the Layouts Container to demisto_client
        Args:
            client: The demisto_client object of the desired XSOAR machine to upload to.

        Returns:
            The result of the upload command from demisto_client
        """
        return client.import_layout(file=self.path)

    def validate(self):
        return self.is_valid_layout()

    def is_valid_layout(self) -> bool:
        """Check whether the layout is valid or not.

        Returns:
            bool. Whether the layout is valid or not
        """
        return all([
            self.is_valid_version(),
            self.is_valid_from_version(),
            self.is_valid_to_version(),
            self.is_to_version_higher_than_from_version(),
            self.is_valid_file_path()
        ])

    def is_valid_version(self):
        # type: () -> bool
        """Base is_valid_version method for files that version is their root.

        Return:
            True if version is valid, else False
        """
        if self.get('version') != DEFAULT_VERSION:
            error_message, error_code = Errors.wrong_version(DEFAULT_VERSION)
            if self.base.handle_error(error_message, error_code, file_path=self.path,
                                      suggested_fix=Errors.suggest_fix(self.path)):
                return False
        return True

    def is_to_version_higher_than_from_version(self) -> bool:
        """Checks if to version field is higher than from version field.

        Returns:
            bool. True if to version field is higher than from version field, else False.
        """
        if self.to_version <= self.from_version:
            error_message, error_code = Errors.from_version_higher_to_version()
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_from_version(self) -> bool:
        """Checks if from version field is valid.

        Returns:
            bool. True if from version field is valid, else False.
        """
        if not self.get('fromVersion') or \
                self.from_version < Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('fromVersion')
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_to_version(self) -> bool:
        """Checks if to version field is valid.

        Returns:
            bool. True if to version field is valid, else False.
        """
        if self.to_version < Version(FROM_VERSION_LAYOUTS_CONTAINER):
            error_message, error_code = Errors.invalid_version_in_layoutscontainer('toVersion')
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_file_path(self) -> bool:
        output_basename = os.path.basename(str(self.path))
        if not output_basename.startswith('layoutscontainer-'):
            error_message, error_code = Errors.invalid_file_path_layoutscontainer(output_basename)
            if self.base.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True
