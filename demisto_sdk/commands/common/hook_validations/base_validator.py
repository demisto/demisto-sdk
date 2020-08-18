import io
import json
import os

import click
from demisto_sdk.commands.common.constants import (PACK_METADATA_CERTIFICATION,
                                                   PACK_METADATA_SUPPORT,
                                                   PACKS_DIR,
                                                   PACKS_PACK_META_FILE_NAME)
from demisto_sdk.commands.common.errors import (ERROR_CODE,
                                                FOUND_FILES_AND_ERRORS,
                                                FOUND_FILES_AND_IGNORED_ERRORS,
                                                PRESET_ERROR_TO_CHECK,
                                                PRESET_ERROR_TO_IGNORE)
from demisto_sdk.commands.common.tools import get_pack_name, get_yaml


class BaseValidator:

    def __init__(self, ignored_errors=None, print_as_warnings=False):
        self.ignored_errors = ignored_errors if ignored_errors else {}
        self.print_as_warnings = print_as_warnings
        self.checked_files = set()

    @staticmethod
    def should_ignore_error(error_code, ignored_errors):
        """Return True is code should be ignored and False otherwise"""
        if ignored_errors is None:
            return False

        # check if specific codes are ignored
        if error_code in ignored_errors:
            return True

        # in case a whole section of codes are selected
        code_type = error_code[:2]
        if code_type in ignored_errors:
            return True

        return False

    def handle_error(self, error_message, error_code, file_path, should_print=True, suggested_fix=None, warning=False,
                     drop_line=False):
        """Handle an error that occurred during validation

        Args:
            drop_line (bool): Whether to drop a line at the beginning of the error message
            warning (bool): Print the error as a warning
            suggested_fix(str): A suggested fix
            error_message(str): The error message
            file_path(str): The file from which the error occurred
            error_code(str): The error code
            should_print(bool): whether the command should be printed

        Returns:
            str. Will return the formatted error message if it is not ignored, an None if it is ignored
        """
        formatted_error = f"{file_path}: [{error_code}] - {error_message}".rstrip("\n") + "\n"

        if drop_line:
            formatted_error = "\n" + formatted_error

        if file_path:
            if not isinstance(file_path, str):
                file_path = str(file_path)

            file_name = os.path.basename(file_path)
            self.check_file_flags(file_name, file_path)

        else:
            file_name = 'No-Name'

        if self.should_ignore_error(error_code, self.ignored_errors.get(file_name)) or warning:
            if self.print_as_warnings or warning:
                click.secho(formatted_error, fg="yellow")
                self.add_to_report_error_list(error_code, file_path, FOUND_FILES_AND_IGNORED_ERRORS)
            return None

        if should_print:
            if suggested_fix:
                click.secho(formatted_error[:-1], fg="bright_red")
                if error_code == 'ST109':
                    click.secho("Please add to the root of the yml a description.\n", fg="bright_red")
                else:
                    click.secho(suggested_fix + "\n", fg="bright_red")

            else:
                click.secho(formatted_error, fg="bright_red")

        self.add_to_report_error_list(error_code, file_path, FOUND_FILES_AND_ERRORS)
        return formatted_error

    def check_file_flags(self, file_name, file_path):
        if file_name not in self.checked_files:
            self.check_deprecated(file_path)
            self.update_checked_flags_by_support_level(file_path)
            self.checked_files.add(file_name)

    def check_deprecated(self, file_path):
        file_name = os.path.basename(file_path)
        if file_path.endswith('.yml'):
            yml_dict = get_yaml(file_path)
            if ('deprecated' in yml_dict and yml_dict['deprecated'] is True) or \
                    (file_name.startswith('playbook') and 'hidden' in yml_dict and
                     yml_dict['hidden'] is True):
                self.add_flag_to_ignore_list(file_path, 'deprecated')

    @staticmethod
    def get_metadata_file_content(meta_file_path):
        with io.open(meta_file_path, mode="r", encoding="utf-8") as file:
            metadata_file_content = file.read()

        return json.loads(metadata_file_content)

    def update_checked_flags_by_support_level(self, file_path):
        pack_name = get_pack_name(file_path)
        if pack_name:
            metadata_path = os.path.join(PACKS_DIR, pack_name, PACKS_PACK_META_FILE_NAME)
            metadata_json = self.get_metadata_file_content(metadata_path)
            support = metadata_json.get(PACK_METADATA_SUPPORT)
            certification = metadata_json.get(PACK_METADATA_CERTIFICATION)

            if support == 'partner':
                if certification is not None and certification != 'certified':
                    self.add_flag_to_ignore_list(file_path, 'non-certified-partner')

            elif support == 'community':
                self.add_flag_to_ignore_list(file_path, 'community')

    @staticmethod
    def create_reverse_ignored_errors_list(errors_to_check):
        ignored_error_list = []
        all_errors = ERROR_CODE.values()
        for error_code in all_errors:
            error_type = error_code[:2]
            if error_code not in errors_to_check and error_type not in errors_to_check:
                ignored_error_list.append(error_code)

        return ignored_error_list

    def add_flag_to_ignore_list(self, file_path, flag):
        additional_ignored_errors = []
        if flag in PRESET_ERROR_TO_IGNORE:
            additional_ignored_errors = PRESET_ERROR_TO_IGNORE[flag]

        elif flag in PRESET_ERROR_TO_CHECK:
            additional_ignored_errors = self.create_reverse_ignored_errors_list(PRESET_ERROR_TO_CHECK[flag])

        file_name = os.path.basename(file_path)
        if file_name in self.ignored_errors:
            self.ignored_errors[file_name].extend(additional_ignored_errors)

        else:
            self.ignored_errors[file_name] = additional_ignored_errors

    @staticmethod
    def add_to_report_error_list(error_code, file_path, error_list):
        formatted_file_and_error = f'{file_path} - [{error_code}]'
        if formatted_file_and_error not in error_list:
            error_list.append(formatted_file_and_error)
