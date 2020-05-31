import os

import click
from demisto_sdk.commands.common.errors import (ERROR_CODE,
                                                PRESET_ERROR_TO_CHECK,
                                                PRESET_ERROR_TO_IGNORE)
from demisto_sdk.commands.common.tools import get_yaml


class BaseValidator:

    def __init__(self, ignored_errors=None, print_as_warnings=False):
        self.ignored_errors = ignored_errors if ignored_errors else {}
        self.print_as_warnings = print_as_warnings
        self.checked_files = []

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

    def handle_error(self, error_massage, error_code, file_path, should_print=True, suggested_fix=None):
        """Handle an error that occurred during validation

        Args:
            suggested_fix(str): A suggested fix
            error_massage(str): The error message
            file_path(str): The file from which the error occurred
            error_code(str): The error code
            should_print(bool): whether the command should be printed

        Returns:
            str. Will return the formatted error message if it is not ignored, an None if it is ignored
        """
        formatted_error = f"{file_path}: [{error_code}] - {error_massage}".rstrip("\n") + "\n"

        if file_path:
            file_name = os.path.basename(file_path)
            self.check_deprecated(file_path)
        else:
            file_name = 'No-Name'

        if self.should_ignore_error(error_code, self.ignored_errors.get('pack')) or \
                self.should_ignore_error(error_code, self.ignored_errors.get(file_name)):
            if self.print_as_warnings:
                click.secho(formatted_error, fg="yellow")
            return None

        if should_print:
            if suggested_fix:
                click.secho(formatted_error[:-1], fg="bright_red")
                click.secho(suggested_fix + "\n", fg="bright_red")

            else:
                click.secho(formatted_error, fg="bright_red")

        return formatted_error

    def check_deprecated(self, file_path):
        file_name = os.path.basename(file_path)
        if file_path.endswith('.yml') and file_name not in self.checked_files:
            yml_dict = get_yaml(file_path)
            if ('deprecated' in yml_dict and yml_dict['deprecated'] is True) or \
                    (file_name.startswith('playbook') and 'hidden' in yml_dict and
                     yml_dict['hidden'] is True):
                self.add_flag_to_ignore_list(file_path, 'deprecated')
            self.checked_files.append(file_name)

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
