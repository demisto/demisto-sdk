import io
import json
import os
from typing import Optional

import click
from demisto_sdk.commands.common.constants import (PACK_METADATA_SUPPORT,
                                                   PACKS_DIR,
                                                   PACKS_PACK_META_FILE_NAME,
                                                   FileType)
from demisto_sdk.commands.common.errors import (FOUND_FILES_AND_ERRORS,
                                                FOUND_FILES_AND_IGNORED_ERRORS,
                                                PRESET_ERROR_TO_CHECK,
                                                PRESET_ERROR_TO_IGNORE,
                                                get_all_error_codes,
                                                get_error_object)
from demisto_sdk.commands.common.tools import (find_type,
                                               get_file_displayed_name,
                                               get_json, get_pack_name,
                                               get_yaml)


class BaseValidator:
    CONTRIBUTOR_TYPE_LIST = ['partner', 'developer', 'community']

    def __init__(self, ignored_errors=None, print_as_warnings=False, suppress_print: bool = False,
                 json_file_path: Optional[str] = None):
        self.ignored_errors = ignored_errors if ignored_errors else {}
        self.print_as_warnings = print_as_warnings
        self.checked_files = set()  # type: ignore
        self.suppress_print = suppress_print
        self.json_file_path = json_file_path

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
                self.json_output(file_path, error_code, error_message, warning)
                self.add_to_report_error_list(error_code, file_path, FOUND_FILES_AND_IGNORED_ERRORS)
            return None

        if should_print and not self.suppress_print:
            if suggested_fix:
                click.secho(formatted_error[:-1], fg="bright_red")
                if error_code == 'ST109':
                    click.secho("Please add to the root of the yml.\n", fg="bright_red")
                else:
                    click.secho(suggested_fix + "\n", fg="bright_red")

            else:
                click.secho(formatted_error, fg="bright_red")

        self.json_output(file_path, error_code, error_message, warning)
        self.add_to_report_error_list(error_code, file_path, FOUND_FILES_AND_ERRORS)
        return formatted_error

    def check_file_flags(self, file_name, file_path):
        if file_name not in self.checked_files:
            self.check_deprecated(file_path)
            self.update_checked_flags_by_support_level(file_path)
            self.checked_files.add(file_name)

    def check_deprecated(self, file_path):
        if file_path.endswith('.yml'):
            yml_dict = get_yaml(file_path)
            if yml_dict.get('deprecated'):
                self.add_flag_to_ignore_list(file_path, 'deprecated')

    @staticmethod
    def get_metadata_file_content(meta_file_path):
        with io.open(meta_file_path, encoding="utf-8") as file:
            metadata_file_content = file.read()

        return json.loads(metadata_file_content)

    def update_checked_flags_by_support_level(self, file_path):
        pack_name = get_pack_name(file_path)
        if pack_name:
            metadata_path = os.path.join(PACKS_DIR, pack_name, PACKS_PACK_META_FILE_NAME)
            metadata_json = self.get_metadata_file_content(metadata_path)
            support = metadata_json.get(PACK_METADATA_SUPPORT)

            if support in ('partner', 'community'):
                self.add_flag_to_ignore_list(file_path, support)

    @staticmethod
    def create_reverse_ignored_errors_list(errors_to_check):
        ignored_error_list = []
        all_errors = get_all_error_codes()
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

    def json_output(self, file_path: str, error_code: str, error_message: str, warning: bool) -> None:
        """Adds an error's info to the output JSON file

        Args:
            file_path (str): The file path where the error ocurred.
            error_code (str): The error code
            error_message (str): The error message
            warning (bool): Whether the error is defined as a warning
        """
        if not self.json_file_path:
            return

        error_data = get_error_object(error_code)

        output = {
            'severity': 'warning' if warning else 'error',
            'errorCode': error_code,
            'message': error_message,
            'ui': error_data.get('ui_applicable'),
            'relatedField': error_data.get('related_field'),
            'linter': 'validate'
        }

        json_contents = []
        if os.path.exists(self.json_file_path):
            existing_json = get_json(self.json_file_path)
            if isinstance(existing_json, list):
                json_contents = existing_json

        file_type = find_type(file_path)
        entity_type = file_type.value if file_type else 'pack'

        # handling unified yml image errors
        if entity_type == FileType.INTEGRATION.value and error_code.startswith('IM'):
            entity_type = FileType.IMAGE.value

        formatted_error_output = {
            'filePath': file_path,
            'fileType': os.path.splitext(file_path)[1].replace('.', ''),
            'entityType': entity_type,
            'errorType': 'Settings',
            'name': get_file_displayed_name(file_path),
            'linter': 'validate',
            **output
        }
        json_contents.append(formatted_error_output)
        with open(self.json_file_path, 'w') as f:
            json.dump(json_contents, f, indent=4)

    def name_does_not_contain_contributor_type_name(self, name: str) -> bool:
        """
        Checks whether pack or integration or script name is contributor supported and has contributor name.
        This validation is needed because the label of contributor is automatically added to the name, so this
        validation will prevent it from being added twice.
        Args:
            name (Dict): Name of the pack/integration/script.
        Returns:
            (bool) True if name contains contributor type name, false otherwise.
        """
        lowercase_name = name.lower()
        return not any(contributor_name in lowercase_name for contributor_name in self.CONTRIBUTOR_TYPE_LIST)

