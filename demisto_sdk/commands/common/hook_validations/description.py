import glob
from typing import Optional

from demisto_sdk.commands.common.constants import (
    BETA_INTEGRATION_DISCLAIMER, PACKS_INTEGRATION_NON_SPLIT_YML_REGEX,
    PACKS_INTEGRATION_YML_REGEX, FileType)
from demisto_sdk.commands.common.errors import FOUND_FILES_AND_ERRORS, Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import find_type, get_yaml, os, re

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
        # Handling a case where the init function initiated with file path instead of structure validator
        self.file_path = file_path.file_path if isinstance(file_path, StructureValidator) else file_path

    def is_valid_file(self):
        self.is_duplicate_description()
        self.verify_demisto_in_description_content()

        # make sure the description is a seperate file
        data_dictionary = get_yaml(self.file_path)
        if not data_dictionary.get('detaileddescription'):
            self.is_valid_description_name()
            self.contains_contrib_details()

        return self._is_valid

    def contains_contrib_details(self):
        """check if DESCRIPTION file contains contribution details"""
        with open(self.file_path) as f:
            description_content = f.read()
        contrib_details = re.findall(rf'### .* {CONTRIBUTOR_DETAILED_DESC}', description_content)
        if contrib_details:
            error_message, error_code = Errors.description_contains_contrib_details()
            if self.handle_error(error_message, error_code, file_path=self.file_path,
                                 suggested_fix=Errors.suggest_fix(self.file_path)):
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

    def is_valid_description_name(self):
        """Check if the description name is valid"""
        description_path = glob.glob(os.path.join(os.path.dirname(self.file_path), '*_description.md'))
        md_paths = glob.glob(os.path.join(os.path.dirname(self.file_path), '*.md'))

        # checking if there are any .md files only for description with a wrong name
        for path in md_paths:
            if path.endswith("README.md") or path.endswith("CHANGELOG.md"):
                md_paths.remove(path)

        if not description_path and md_paths:
            error_message, error_code = Errors.invalid_description_name()

            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self._is_valid = False
                return False

        return True

    def verify_demisto_in_description_content(self):
        """
        Checks if there are the word 'Demisto' in the description content.

        Return:
            True if 'Demisto' does not exist in the description content, and False if it does.
        """
        description_path = ''
        yml_line_num = 0
        yml_or_file = ''

        # case 1 the file path is for an integration
        if find_type(self.file_path) in [FileType.INTEGRATION, FileType.BETA_INTEGRATION]:
            integration_path = self.file_path
            data_dictionary = get_yaml(self.file_path)
            is_unified_integration = data_dictionary.get('script', {}).get('script', '') not in {'-', ''}

            if is_unified_integration:
                description_content = data_dictionary.get('detaileddescription', '')
                yml_or_file = 'in the yml file'

                # find in which line the description begins in the yml
                with open(self.file_path, 'r') as f:
                    for line_n, line in enumerate(f.readlines()):
                        if 'detaileddescription:' in line:
                            yml_line_num = line_n + 1

            # if not found try and look for the description file path
            else:
                yml_or_file = 'in the description file'
                description_path = f'{os.path.splitext(self.file_path)[0]}_description.md'

                if not os.path.exists(description_path):
                    error_message, error_code = Errors.no_description_file_warning()
                    self.handle_error(error_message, error_code, file_path=self.file_path, warning=True)
                    return True

        # running on a description file so the file path is the description path
        else:
            description_path = self.file_path
            integration_path = self.file_path.replace('_description.md', '.yml')
            yml_or_file = 'in the description file'

        if description_path:
            with open(description_path) as f:
                description_content = f.read()

        invalid_lines = []
        for line_num, line in enumerate(description_content.split('\n')):
            if 'demisto ' in line.lower() or ' demisto' in line.lower():
                invalid_lines.append(line_num + yml_line_num + 1)

        if invalid_lines:
            error_message, error_code = Errors.description_contains_demisto_word(invalid_lines, yml_or_file)

            # print only if the error is not already in the report
            check_in_report = f'{integration_path} - [{error_code}]'
            if self.handle_error(error_message, error_code, file_path=integration_path,
                                 should_print=check_in_report not in FOUND_FILES_AND_ERRORS):
                self._is_valid = False
                return False

        return True
