import glob
from typing import Optional

from demisto_sdk.commands.common.constants import (
    BETA_INTEGRATION_DISCLAIMER, PACKS_INTEGRATION_NON_SPLIT_YML_REGEX,
    PACKS_INTEGRATION_YML_REGEX)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import get_yaml, os, re

CONTRIBUTOR_DETAILED_DESC = 'Contributed Integration'


class DescriptionValidator(BaseValidator):
    """DescriptionValidator was designed to make sure we provide a detailed description properly.

    Attributes:
        file_path (string): Path to the checked file.
        _is_valid (bool): the attribute which saves the valid/in-valid status of the current file.
    """

    def __init__(self, file_path: str, ignored_errors=None, print_as_warnings=False, suppress_print: bool = False,
                 json_file_path: Optional[str] = None):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self._is_valid = True

        self.file_path = file_path

    def is_valid(self):
        self.is_duplicate_description()

        return self._is_valid

    def is_valid_file(self):
        """check if DESCRIPTION file contains contribution details"""
        with open(self.file_path) as f:
            description_content = f.read()
        contrib_details = re.findall(rf'### .* {CONTRIBUTOR_DETAILED_DESC}', description_content)
        if contrib_details:
            error_message, error_code = Errors.description_contains_contrib_details()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False
        return True

    def is_valid_beta_description(self):
        """Check if beta disclaimer exists in detailed description"""
        data_dictionary = get_yaml(self.file_path)
        description_in_yml = data_dictionary.get('detaileddescription', '') if data_dictionary else ''

        if not re.match(PACKS_INTEGRATION_NON_SPLIT_YML_REGEX, self.file_path, re.IGNORECASE):
            try:
                md_file_path = glob.glob(os.path.join(os.path.dirname(self.file_path), '*_description.md'))[0]
            except IndexError:
                error_message, error_code = Errors.description_missing_in_beta_integration()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self._is_valid = False
                    return False

            with open(md_file_path) as description_file:
                description = description_file.read()
            if BETA_INTEGRATION_DISCLAIMER not in description:
                error_message, error_code = Errors.no_beta_disclaimer_in_description()
                if self.handle_error(error_message, error_code, file_path=self.file_path):
                    self._is_valid = False
                    return False
            else:
                return True
        elif BETA_INTEGRATION_DISCLAIMER not in description_in_yml:
            error_message, error_code = Errors.no_beta_disclaimer_in_yml()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False

        return True

    def is_duplicate_description(self):
        """Check if the integration has a non-duplicate description ."""
        is_description_in_yml = False
        is_description_in_package = False
        package_path = None
        md_file_path = None

        data_dictionary = get_yaml(self.file_path)

        if not re.match(PACKS_INTEGRATION_YML_REGEX, self.file_path, re.IGNORECASE):
            package_path = os.path.dirname(self.file_path)
            try:
                path_without_extension = os.path.splitext(self.file_path)[0]
                md_file_path = glob.glob(path_without_extension + '_description.md')[0]
            except IndexError:
                is_unified_integration = data_dictionary.get('script', {}).get('script', '') not in {'-', ''}
                if not (data_dictionary.get('deprecated') or is_unified_integration):
                    error_message, error_code = Errors.no_description_file_warning()
                    self.handle_error(error_message, error_code, file_path=self.file_path, warning=True)

            if md_file_path:
                is_description_in_package = True

        if not data_dictionary:
            return is_description_in_package

        if data_dictionary.get('detaileddescription'):
            is_description_in_yml = True

        if is_description_in_package and is_description_in_yml:
            error_message, error_code = Errors.description_in_package_and_yml()
            if self.handle_error(error_message, error_code, file_path=package_path):
                self._is_valid = False
                return False

        return True
