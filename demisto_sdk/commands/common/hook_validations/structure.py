"""Structure Validator for Demisto files

Module contains validation of schemas, ids and paths.
"""
import json
import logging
import os
import re
from typing import Optional, Tuple

import yaml
from demisto_sdk.commands.common.configuration import Configuration
from demisto_sdk.commands.common.constants import (
    ACCEPTED_FILE_EXTENSIONS, FILE_TYPES_PATHS_TO_VALIDATE,
    JSON_ALL_REPUTATIONS_INDICATOR_TYPES_REGEXES, SCHEMA_TO_REGEX, FileType)
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator
from demisto_sdk.commands.common.tools import (checked_type,
                                               get_content_file_type_dump,
                                               get_matching_regex,
                                               get_remote_file)
from demisto_sdk.commands.format.format_constants import \
    OLD_FILE_DEFAULT_1_FROMVERSION
from pykwalify.core import Core


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
                 configuration=Configuration(), ignored_errors=None, print_as_warnings=False, tag='master'):
        super().__init__(ignored_errors=ignored_errors, print_as_warnings=print_as_warnings)
        self.is_valid = True
        self.valid_extensions = ['.yml', '.json', '.md', '.png']
        self.file_path = file_path.replace('\\', '/')

        self.scheme_name = predefined_scheme or self.scheme_of_file_by_path()
        if isinstance(self.scheme_name, str):
            self.scheme_name = FileType(self.scheme_name)

        self.file_type = self.get_file_type()
        self.current_file = self.load_data_from_file()
        self.fromversion = fromversion
        if is_new_file or predefined_scheme:
            self.old_file = {}
        else:
            self.old_file = get_remote_file(old_file_path if old_file_path else file_path, tag=tag)
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
            if get_matching_regex(self.file_path, regex_list):
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
        if self.scheme_name in [None, FileType.IMAGE, FileType.README, FileType.RELEASE_NOTES, FileType.TEST_PLAYBOOK]:
            return True
        # ignore reputations.json
        if checked_type(self.file_path, JSON_ALL_REPUTATIONS_INDICATOR_TYPES_REGEXES):
            return True
        try:
            # disabling massages of level INFO and beneath of pykwalify such as: INFO:pykwalify.core:validation.valid
            log = logging.getLogger('pykwalify.core')
            log.setLevel(logging.WARNING)
            scheme_file_name = 'integration' if self.scheme_name.value == 'betaintegration' else self.scheme_name.value
            path = os.path.normpath(
                os.path.join(__file__, "..", "..", self.SCHEMAS_PATH, '{}.yml'.format(scheme_file_name)))
            core = Core(source_file=self.file_path,
                        schema_files=[path])
            core.validate(raise_exception=True)
        except Exception as err:
            try:
                error_message, error_code = self.parse_error_msg(err)
                if self.handle_error(error_message, error_code, self.file_path,
                                     suggested_fix=Errors.suggest_fix(self.file_path)):
                    self.is_valid = False
                    return False
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

    def parse_error_msg(self, err) -> Tuple[str, str]:
        """A wrapper which runs the print error message for a list of errors in yaml
        Returns:
            str, str: parsed error message from pykwalify
        """
        if ".\n" in str(err):
            for error in str(err).split('.\n'):
                return self.parse_error_line(error)
        else:
            return self.parse_error_line(str(err))

        # should not get here
        return '', ''

    def parse_error_line(self, err) -> Tuple[str, str]:
        """Returns a parsed error message from pykwalify
        Args: an schema error message from pykwalify
        """
        # err example: '<SchemaError: error code 2: Schema validation failed:
        #  - Cannot find required key \'description\'. Path: \'\''
        step_1 = str(err).split('Path: ')
        # step_1 example: ["<SchemaError: error code 2: Schema validation failed:\n - Cannot find required key
        # 'description'. ", "'/script/commands/0/outputs/20'.: ", "'/'>"]
        step_2 = step_1[1]
        # step_2 example: '\'/script/commands/0/outputs/20\'.: '
        step_3 = step_2[2:-4]
        # step_3 example: 'script/commands/0/outputs/20'
        error_path = step_3.split('/')
        # error_path example: ['script', 'commands', '0', 'outputs', '20']

        # check if the Path from the error is '' :
        if isinstance(error_path, list) and error_path[0]:
            curr = self.current_file
            key_from_error = str(err).split('key')[1].split('.')[0].replace("'", '-').split('-')[1]
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
                    curr = curr.get(single_path)
                    key_list.append(single_path)

            curr_string_transformer = get_content_file_type_dump(self.file_path)

            # if the error is from arguments of file
            if curr.get('name'):
                return Errors.pykwalify_missing_parameter(str(key_from_error),
                                                          curr_string_transformer(curr.get('name')),
                                                          str(key_list).strip('[]').replace(',', '->'))

            # if the error is from outputs of file
            elif curr.get('contextPath'):
                return Errors.pykwalify_missing_parameter(str(key_from_error),
                                                          curr_string_transformer(curr.get('contextPath')),
                                                          str(key_list).strip('[]').replace(',', '->'))
            # if the error is from neither arguments , outputs nor root
            else:
                return Errors.pykwalify_missing_parameter(str(key_from_error), curr_string_transformer(curr),
                                                          str(key_list).strip('[]').replace(',', '->'))
        else:
            err_msg = str(err).lower()
            if 'key' in err_msg:
                key_from_error = err_msg.split('key')[1].split('.')[0].replace("'", '-').split('-')[1]

                if 'not defined' in err_msg:
                    return Errors.pykwalify_field_undefined(str(key_from_error))

                else:
                    return Errors.pykwalify_missing_in_root(str(key_from_error))

        # should not get here
        return '', ''

    def check_for_spaces_in_file_name(self):
        file_name = os.path.basename(self.file_path)
        if file_name.count(' ') > 0:
            error_message, error_code = Errors.file_name_include_spaces_error(file_name)
            if self.handle_error(error_message, error_code, self.file_path):
                return False

        return True
