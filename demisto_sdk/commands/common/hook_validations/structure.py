"""Structure Validator for Demisto files

Module contains validation of schemas, ids and paths.
"""
import json
import logging
import os
import re
import string
from typing import List, Optional, Tuple

import click
import yaml
from pykwalify.core import Core

from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    ACCEPTED_FILE_EXTENSIONS, CHECKED_TYPES_REGEXES,
    FILE_TYPES_PATHS_TO_VALIDATE, OLD_REPUTATION, SCHEMA_TO_REGEX, FileType)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (get_remote_file,
                                               is_file_path_in_pack)
from demisto_sdk.commands.format.format_constants import \
    OLD_FILE_DEFAULT_1_FROMVERSION


class StructureValidator(BaseValidator):
    """Structure validator is designed to validate the correctness of the file structure we enter to content repo.

        Attributes:
            file_path (str): the path to the file we are examining at the moment.
            is_valid (bool): the attribute which saves the valid/in-valid status of the current file. will be bool only
                             after running is_file_valid.
            scheme_name (str): Name of the yaml scheme need to validate.
            file_type (str): equal to scheme_name if there's a scheme.
            current_file (dict): loaded json.
            old_file: (dict) loaded file from git.
            fromversion (bool): Set True if fromversion was changed on file.
        """
    SCHEMAS_PATH = "schemas"

    FILE_SUFFIX_TO_LOAD_FUNCTION = {
        '.yml': yaml.safe_load,
        '.json': json.load,
    }

    def __init__(self, file_path, is_new_file=False, old_file_path=None, predefined_scheme=None, fromversion=False,
                 configuration=Configuration(), ignored_errors=None, print_as_warnings=False, tag='master',
                 suppress_print: bool = False, branch_name='', json_file_path=None, skip_schema_check=False,
                 pykwalify_logs=False, quite_bc=False):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings,
                         suppress_print=suppress_print, json_file_path=json_file_path)
        self.is_valid = True
        self.valid_extensions = ['.yml', '.json', '.md', '.png']
        self.file_path = file_path.replace('\\', '/')
        self.skip_schema_check = skip_schema_check
        self.pykwalify_logs = pykwalify_logs
        self.quite_bc = quite_bc

        self.scheme_name = predefined_scheme or self.scheme_of_file_by_path()
        if isinstance(self.scheme_name, str):
            self.scheme_name = FileType(self.scheme_name)

        self.prev_ver = tag
        self.branch_name = branch_name
        self.file_type = self.get_file_type()
        self.current_file = self.load_data_from_file()
        self.fromversion = fromversion
        # If it is a newly added file or if it is a file outside the pack then we will not search for an old file
        if is_new_file or not is_file_path_in_pack(self.file_path):
            self.old_file = {}
        else:
            self.old_file = get_remote_file(old_file_path if old_file_path else file_path, tag=tag,
                                            suppress_print=suppress_print)
        self.configuration = configuration

    def is_valid_file(self):
        # type: () -> bool
        """Checks if given file is valid

        Returns:
            (bool): Is file is valid
        """
        if self.check_for_spaces_in_file_name() and self.is_valid_file_extension():
            answers = [
                self.is_valid_file_path(),
                self.is_valid_scheme(),
                self.is_file_id_without_slashes(),
            ]

            if self.old_file:  # In case the file is modified
                click.secho(f'Validating backwards compatibility for {self.file_path}')
                answers.append(not self.is_id_modified())
                answers.append(self.is_valid_fromversion_on_modified())

            return all(answers)

        return False

    def scheme_of_file_by_path(self):
        # type:  () -> Optional[str]
        """Running on given regexes from `constants` to find out what type of file it is

        Returns:
            (str): Type of file by scheme name
        """

        for scheme_name, regex_list in SCHEMA_TO_REGEX.items():
            if checked_type_by_reg(self.file_path, regex_list):
                return scheme_name

        pretty_formatted_string_of_regexes = json.dumps(SCHEMA_TO_REGEX, indent=4, sort_keys=True)

        error_message, error_code = Errors.structure_doesnt_match_scheme(pretty_formatted_string_of_regexes)
        self.handle_error(error_message, error_code, file_path=self.file_path)

        return None

    def is_valid_scheme(self):
        # type: () -> bool
        """Validate the file scheme according to the scheme we have saved in SCHEMAS_PATH.

        Returns:
            bool. Whether the scheme is valid on self.file_path.
        """
        # ignore schema checks for unsupported file types, reputations.json or is skip-schema-check is set.
        if self.scheme_name in [None, FileType.IMAGE, FileType.README, FileType.RELEASE_NOTES, FileType.TEST_PLAYBOOK,
                                FileType.AUTHOR_IMAGE] \
                or self.skip_schema_check or (self.scheme_name == FileType.REPUTATION and
                                              os.path.basename(self.file_path) == OLD_REPUTATION):
            return True

        click.secho(f'Validating scheme for {self.file_path}')

        try:
            # disabling massages of level ERROR and beneath of pykwalify such as: INFO:pykwalify.core:validation.valid
            log = logging.getLogger('pykwalify.core')
            log.setLevel(logging.CRITICAL)
            if self.pykwalify_logs:
                # reactivating pykwalify ERROR level logs
                logging.disable(logging.ERROR)
            scheme_file_name = 'integration' if self.scheme_name.value == 'betaintegration' else self.scheme_name.value  # type: ignore
            path = os.path.normpath(
                os.path.join(__file__, "..", "..", self.SCHEMAS_PATH, '{}.yml'.format(scheme_file_name)))
            core = Core(source_file=self.file_path,
                        schema_files=[path])
            core.validate(raise_exception=True)
        except Exception as err:
            try:
                return self.parse_error_msg(err)
            except Exception:
                error_message, error_code = Errors.pykwalify_general_error(err)
                if self.handle_error(error_message, error_code, self.file_path):
                    self.is_valid = False
                    return False
        return True

    @staticmethod
    def get_file_id_from_loaded_file_data(loaded_file_data):
        # type: (dict) -> Optional[str]
        """Gets a dict and extracting its `id` field

        Args:
            loaded_file_data: Data to find dict

        Returns:
            (str or None): file ID if exists.
        """
        try:
            file_id = loaded_file_data.get('id')
            if not file_id:
                # In integrations/scripts, the id is under 'commonfields'.
                file_id = loaded_file_data.get('commonfields', {}).get('id', '')
            if not file_id:
                # In layout, the id is under 'layout'.
                file_id = loaded_file_data.get('layout', {}).get('id', '')

            return file_id
        except AttributeError:
            return None

    def is_file_id_without_slashes(self):
        # type: () -> bool
        """Check if the ID of the file contains any slashes ('/').

        Returns:
            bool. Whether the file's ID contains slashes or not.
        """
        file_id = self.get_file_id_from_loaded_file_data(self.current_file)
        if file_id and '/' in file_id:
            error_message, error_code = Errors.file_id_contains_slashes()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def is_id_modified(self):
        # type: () -> bool
        """Check if the ID of the file has been changed.


        Returns:
            (bool): Whether the file's ID has been modified or not.
        """
        if not self.old_file:
            return False

        old_version_id = self.get_file_id_from_loaded_file_data(self.old_file)
        new_file_id = self.get_file_id_from_loaded_file_data(self.current_file)
        if not (new_file_id == old_version_id):
            error_message, error_code = Errors.file_id_changed(old_version_id, new_file_id)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return True

        # False - the id has not changed.
        return False

    def is_valid_fromversion_on_modified(self):
        # type: () -> bool
        """Check that the fromversion property was not changed on existing Content files.

        Returns:
            (bool): Whether the files' fromversion as been modified or not.
        """
        if not self.old_file:
            return True

        from_version_new = self.current_file.get("fromversion") or self.current_file.get("fromVersion")
        from_version_old = self.old_file.get("fromversion") or self.old_file.get("fromVersion")

        # if in old file there was no fromversion ,format command will add from version key with 1.0.0
        if not from_version_old and from_version_new == OLD_FILE_DEFAULT_1_FROMVERSION:
            return True

        if from_version_old != from_version_new:
            error_message, error_code = Errors.from_version_modified()
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                self.is_valid = False
                return False

        return True

    def is_valid_file_extension(self):
        file_extension = os.path.splitext(self.file_path)[1]
        if file_extension not in self.valid_extensions:
            error_message, error_code = Errors.wrong_file_extension(file_extension, self.valid_extensions)
            if self.handle_error(error_message, error_code, file_path=self.file_path):
                return False

        return True

    def load_data_from_file(self):
        # type: () -> dict
        """Loads data according to function defined in FILE_SUFFIX_TO_LOAD_FUNCTION
        Returns:
             (dict)
        """
        file_extension = os.path.splitext(self.file_path)[1]
        if file_extension in ACCEPTED_FILE_EXTENSIONS:
            if file_extension in self.FILE_SUFFIX_TO_LOAD_FUNCTION:
                load_function = self.FILE_SUFFIX_TO_LOAD_FUNCTION[file_extension]
                with open(self.file_path, 'r') as file_obj:
                    loaded_file_data = load_function(file_obj)  # type: ignore
                    return loaded_file_data

            # Ignore loading image and markdown
            elif file_extension in ['.png', '.md']:
                return {}

        return {}

    def get_file_type(self):
        # type: () -> Optional[str]
        """Gets file type based on regex or scheme_name

        Returns:
            str if valid filepath, else None
        """
        # If scheme_name exists, already found that the file is in the right path
        if self.scheme_name:
            if isinstance(self.scheme_name, str):
                return self.scheme_name
            return self.scheme_name.value

        for file_type, regexes in FILE_TYPES_PATHS_TO_VALIDATE.items():
            for regex in regexes:
                if re.search(regex, self.file_path, re.IGNORECASE):
                    return file_type
        return None

    def is_valid_file_path(self):
        """Returns is valid filepath exists.

        Can be only if file_type or scheme_name exists (runs from init)

        Returns:
            True if valid file path else False
        """
        is_valid_path = bool(self.scheme_name or self.file_type)
        if not is_valid_path:
            error_message, error_code = Errors.invalid_file_path()
            if not self.handle_error(error_message, error_code, file_path=self.file_path):
                is_valid_path = True
        return is_valid_path

    def parse_error_msg(self, err) -> bool:
        """A wrapper which handles pykwalify error messages.
        Returns:
            bool. Indicating if the schema is valid.
        """
        lines = str(err).split('\n')
        valid = True
        for line in lines:
            if line.lstrip().startswith('-'):
                error_message, error_code, suggest_format = self.parse_error_line(line)

                if suggest_format:
                    if self.handle_error(error_message, error_code, self.file_path,
                                         suggested_fix=Errors.suggest_fix(self.file_path)):
                        self.is_valid = False
                        valid = False

                elif self.handle_error(error_message, error_code, self.file_path):
                    self.is_valid = False
                    valid = False

        return valid

    def parse_error_line(self, error_line: str) -> Tuple[str, str, bool]:
        """Identifies the pykwalify error type and reformat it to a more readable output.

        Arguments:
            error_line (str): pykwalify error line.

        Returns:
            str, str, bool: the validate error message, error code
            and whether to suggest running format as a possible fix.
        """

        error_path = self.get_error_path(error_line)
        if 'Cannot find required key' in error_line:
            return self.parse_missing_key_line(error_path, error_line)

        elif 'was not defined' in error_line:
            return self.parse_undefined_key_line(error_path, error_line)

        elif 'Enum' in error_line:
            return self.parse_enum_error_line(error_path, error_line)

        else:
            raise ValueError("Could not identify error type")

    def get_error_path(self, error_line: str) -> List[str]:
        """Extract the error path from the pykwalify error line.

        Arguments:
            error_line (str): pykwalify error line.

        Returns:
            list: A list of strings indicating the path to the pykwalify error location.
        """
        # err example: '- Cannot find required key \'description\'. Path: \'\''
        step_1 = str(error_line).split('Path: ')
        # step_1 example: ["- Cannot find required key description'. ", "'/script/commands/0/outputs/20'.: ", "'/'>"]
        step_2 = step_1[1]
        # step_2 example: "'/category' Enum: ['Analytics & SIEM', 'Utilities', 'Messaging']"
        step_3 = step_2.split('Enum')[0] if 'Enum' in step_2 else step_2
        # step_3 example: '\'/script/commands/0/outputs/20\'.: '
        step_4 = step_3.split('/')
        # step_4 example: ["\'script", "commands", "0", "outputs" "20\'.: "]'
        error_path = self.clean_path(step_4)
        # error_path example: ['script', 'commands', '0', 'outputs', '20']
        return error_path

    def clean_path(self, path: List[str]) -> List[str]:
        """Cleans extra punctuation from pykwalify error path

        Arguments:
            path (list): list indicating the pykwalify error path.

        Returns:
            list: A list of strings indicating the path to the pykwalify error location.
        """
        clean_path = []
        table = str.maketrans(dict.fromkeys(string.punctuation))
        for part in path:
            clean_part = part.translate(table).strip()
            if clean_part:
                clean_path.append(clean_part)

        return clean_path

    def parse_missing_key_line(self, error_path: List[str], error_msg: str) -> Tuple[str, str, bool]:
        """Parse a missing key pykwalify error.

        Arguments:
            error_path (list): list indicating the pykwalify error path.
            error_msg (str): The pykwalify error line.

        Returns:
            str, str, bool: the validate error message, code and whether to suggest format as a possible fix
        """
        # error message example:  - Cannot find required key 'version'. Path: '/commonfields'.
        error_key = str(error_msg).split('key')[1].split('.')[0].replace("'", "").strip()
        if error_path:
            error_path_str = self.translate_error_path(error_path)
            error_message, error_code = Errors.pykwalify_missing_parameter(str(error_key), error_path_str)
            return error_message, error_code, True

        # if no path found this is an error in root
        else:
            error_message, error_code = Errors.pykwalify_missing_in_root(str(error_key))
            return error_message, error_code, True

    def parse_undefined_key_line(self, error_path: List[str], error_msg: str) -> Tuple[str, str, bool]:
        """Parse a undefined key pykwalify error.

        Arguments:
            error_path (list): list indicating the pykwalify error path.
            error_msg (str): The pykwalify error line.

        Returns:
            str, str, bool: the validate error message, code and whether to suggest format as a possible fix
        """
        # error message example: - Key 'ok' was not defined. Path: '/configuration/0'.
        error_key = str(error_msg).split('Key')[1].split(' ')[1].replace("'", "").strip()
        if error_path:
            error_path_str = self.translate_error_path(error_path)
            error_message, error_code = Errors.pykwalify_field_undefined_with_path(str(error_key), error_path_str)
            return error_message, error_code, True

        else:
            error_message, error_code = Errors.pykwalify_field_undefined(str(error_key))
            return error_message, error_code, True

    def parse_enum_error_line(self, error_path: List[str], error_msg: str) -> Tuple[str, str, bool]:
        """Parse a wrong enum value pykwalify error.

        Arguments:
            error_path (list): list indicating the pykwalify error path.
            error_msg (str): The pykwalify error line.

        Returns:
            str, str, bool: the validate error message, code and whether to suggest format as a possible fix
        """
        # error message example: - Enum 'Network Securitys' does not exist.
        # Path: '/category' Enum: ['Analytics & SIEM', 'Utilities', 'Messaging'].
        wrong_enum = str(error_msg).split('Enum ')[1].split('does')[0].replace("'", "").strip()
        possible_values = str(error_msg).split('Enum:')[-1].strip(' [].')
        error_message, error_code = Errors.pykwalify_incorrect_enum(self.translate_error_path(error_path),
                                                                    wrong_enum, possible_values)
        return error_message, error_code, False

    def translate_error_path(self, error_path: List[str]) -> str:
        """Parse pykwalify error path to a more easy to read path.

        Arguments:
            error_path (list): list indicating the pykwalify error path.

        Returns:
            str: a string indicating a path to the pykwalify error.
        """
        curr = self.current_file
        key_list = []
        for single_path in error_path:
            if type(curr) is list:
                curr = curr[int(single_path)]

                # if the error is from arguments of file
                if curr.get('name'):
                    key_list.append(curr.get('name'))

                # if the error is from outputs of file
                elif curr.get('contextPath'):
                    key_list.append(curr.get('contextPath'))

                else:
                    key_list.append(single_path)
            else:
                curr = curr.get(single_path)  # type: ignore
                key_list.append(single_path)

        return str(key_list).strip('[]').replace(',', '->')

    def check_for_spaces_in_file_name(self):
        file_name = os.path.basename(self.file_path)
        if file_name.count(' ') > 0:
            error_message, error_code = Errors.file_name_include_spaces_error(file_name)
            if self.handle_error(error_message, error_code, self.file_path):
                return False

        return True


    def is_valid_yaml(self):
        # type: () -> bool
        """Checks if given file is valid

        Returns:
            (bool): Is file is valid
        """
        try:
            with open(self.file_path, 'r') as yf:
                yaml_obj = ryaml.load(yf)
        except Exception as e:
            error_message, error_code = Errors.invalid_yml_file(e)
            self.handle_error(error_message, error_code, file_path=self.file_path)
            return false
        return true


def checked_type_by_reg(file_path, compared_regexes=None, return_regex=False):
    """ Check if file_path matches the given regexes or any reg from the CHECKED_TYPES_REGEXES list which contains all
     supported file regexes.

    Args:
        file_path: (str) on which the check is done.
        compared_regexes: (list) of str which represent the regexes that will be check on file_path.
        return_regex: (bool) Whether the function will return the regex that was matched or not.

    Returns:
            String/Bool
            Depends on if return_regex was set to True or False.
            Returns Bool when the return_regex is False and the return value is whether any regex was matched or not.
            Returns String when the return_regex is True and the return value is the regex that was found as a match.

    """
    compared_regexes = compared_regexes or CHECKED_TYPES_REGEXES
    for regex in compared_regexes:
        if re.search(regex, file_path, re.IGNORECASE):
            if return_regex:
                return regex
            return True
    return False
