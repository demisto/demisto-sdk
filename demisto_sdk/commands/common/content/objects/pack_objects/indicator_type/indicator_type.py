import re
from typing import Union

from demisto_sdk.commands.common.constants import (DEFAULT_VERSION,
                                                   FEATURE_BRANCHES,
                                                   INDICATOR_TYPE,
                                                   OLD_INDICATOR_TYPE,
                                                   OLDEST_SUPPORTED_VERSION)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import get_remote_file
from packaging.version import Version
from wcmatch.pathlib import Path

# Valid indicator type can include letters, numbers whitespaces, ampersands and underscores.
VALID_INDICATOR_TYPE = '^[A-Za-z0-9_& ]*$'


class IndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, INDICATOR_TYPE)
        self.handle_error = BaseValidator().handle_error
        self.prev_ver = 'master',
        self.branch_name = ''

    def validate(self, ignored_errors, print_as_warnings, prev_ver, branch_name):
        self.handle_error = BaseValidator(ignored_errors=ignored_errors,
                                          print_as_warnings=print_as_warnings).handle_error
        self.prev_ver = prev_ver
        self.branch_name = branch_name
        old_file = get_remote_file(self.path, tag=prev_ver)
        return self.is_valid_file(old_file)

    def is_valid_file(self, old_file):
        """Check whether the reputation file is valid or not
        """

        is_reputation_valid = all([
            self.is_valid_fromversion(),
            self.is_valid_version(),
            self.is_valid_expiration(),
            self.is_required_fields_empty(),
            self.is_valid_indicator_type_id()
        ])

        # check only on added files
        if not old_file:
            is_reputation_valid = all([
                is_reputation_valid,
                self.is_id_equals_details()
            ])

        return is_reputation_valid

    def is_valid_version(self):
        # type: () -> bool
        """Validate that the reputations file as version of -1."""
        is_valid = True

        internal_version = self.get('version')
        if internal_version != DEFAULT_VERSION:
            object_id = self.get('id')
            error_message, error_code = Errors.wrong_version_reputations(object_id, DEFAULT_VERSION)

            if self.handle_error(error_message, error_code, file_path=self.path):
                is_valid = False

        return is_valid

    def is_valid_expiration(self):
        # type: () -> bool
        """Validate that the expiration field of a 5.5 reputation file is numeric."""
        if self.from_version >= Version("5.5.0"):
            expiration = self.get('expiration', "")
            if not isinstance(expiration, int) or expiration < 0:
                error_message, error_code = Errors.reputation_expiration_should_be_numeric()
                if self.handle_error(error_message, error_code, file_path=self.path):
                    return False

        return True

    def is_required_fields_empty(self):
        # type: () -> bool
        """Validate that id and details fields are not empty.
        Returns:
            bool. True if id and details fields are not empty, False otherwise.
        """
        id_ = self.get('id', None)
        details = self.get('details', None)
        if not id_ or not details:
            error_message, error_code = Errors.reputation_empty_required_fields()
            if self.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_id_equals_details(self):
        # type: () -> bool
        """Validate that the id equal details."""
        id_ = self.get('id', None)
        details = self.get('details', None)
        if id_ and details and id_ != details:
            error_message, error_code = Errors.reputation_id_and_details_not_equal()
            if self.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def is_valid_indicator_type_id(self):
        # type: () -> bool
        """Validate that id field is valid.
        Returns:
            bool. True if id field is valid, False otherwise.
        """
        id_ = self.get('id', None)
        if id_ and not re.match(VALID_INDICATOR_TYPE, id_):
            error_message, error_code = Errors.reputation_invalid_indicator_type_id()
            if self.handle_error(error_message, error_code, file_path=self.path):
                return False
        return True

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.prev_ver or feature_branch_name in self.branch_name)
               for feature_branch_name in FEATURE_BRANCHES) or str(self.path).endswith('reputations.json'):
            return False

        return True

    def is_valid_fromversion(self):
        """Check if the file has a fromversion 5.0.0 or higher
            This is not checked if checking on or against a feature branch.
        """
        if not self.should_run_fromversion_validation():
            return True

        if self.from_version < Version(OLDEST_SUPPORTED_VERSION):
            error_message, error_code = Errors.no_minimal_fromversion_in_file('fromVersion',
                                                                              OLDEST_SUPPORTED_VERSION)
            if self.handle_error(error_message, error_code, file_path=self.path):
                return False

        return True


class OldIndicatorType(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, OLD_INDICATOR_TYPE)

    def normalize_file_name(self) -> str:
        """Add prefix to file name if not exists.

        Examples:
            1. "hello-world.yml" -> "reputations.json"
            2. "reputations.json" -> "reputations.json"

        Returns:
            str: Normalize file name.
        """
        return "reputations.json"
