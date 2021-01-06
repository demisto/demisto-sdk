from typing import Union

from demisto_sdk.commands.common.constants import (FEATURE_BRANCHES,
                                                   OLDEST_SUPPORTED_VERSION,
                                                   REPORT)
from demisto_sdk.commands.common.content.objects.pack_objects.abstract_pack_objects.json_content_object import \
    JSONContentObject
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from packaging.version import Version
from wcmatch.pathlib import Path


class Report(JSONContentObject):
    def __init__(self, path: Union[Path, str]):
        super().__init__(path, REPORT)
        self.handle_error = BaseValidator().handle_error
        self.prev_ver = 'master'
        self.branch_name = ''

    def validate(self, ignored_errors, print_as_warnings, prev_ver, branch_name):
        self.handle_error = BaseValidator(ignored_errors=ignored_errors,
                                          print_as_warnings=print_as_warnings).handle_error
        self.prev_ver = prev_ver
        self.branch_name = branch_name

        return self.is_valid_fromversion()

    def should_run_fromversion_validation(self):
        # skip check if the comparison is to a feature branch or if you are on the feature branch itself.
        # also skip if the file in question is reputations.json
        if any((feature_branch_name in self.prev_ver or feature_branch_name in self.branch_name)
               for feature_branch_name in FEATURE_BRANCHES):
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
