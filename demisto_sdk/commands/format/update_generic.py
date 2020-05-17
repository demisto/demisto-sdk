import os
from typing import List, Union

import yaml
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_dict_from_file,
                                               get_remote_file,
                                               is_file_from_content_repo,
                                               print_color)
from demisto_sdk.commands.format.format_constants import (
    DEFAULT_VERSION, ERROR_RETURN_CODE, NEW_FILE_DEFAULT_5_FROMVERSION,
    OLD_FILE_DEFAULT_1_FROMVERSION, SKIP_RETURN_CODE, SUCCESS_RETURN_CODE)
from ruamel.yaml import YAML

ryaml = YAML()
ryaml.allow_duplicate_keys = True
ryaml.preserve_quotes = True  # type: ignore


class BaseUpdate:
    """BaseUpdate is the base class for all format commands.
        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file (str): the desired file name to save the updated version of the YML to.
            relative_content_path (str): Relative content path of output path.
            old_file (dict): Data of old file from content repo, if exist.
            schema_path (str): Schema path of file.
            from_version (str): Value of Wanted fromVersion key in file.
            data (dict): Dictionary of loaded file.
            file_type (str): Whether the file is yml or json.
            from_version_key (str): The fromVersion key in file, different between yml and json files.
    """

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '', no_validate: bool = False):
        self.source_file = input
        self.output_file = self.set_output_file_path(output)
        _, self.relative_content_path = is_file_from_content_repo(self.output_file)
        self.old_file = self.is_old_file(self.relative_content_path if self.relative_content_path else self.output_file)
        self.schema_path = path
        self.from_version = from_version
        self.no_validate = no_validate

        if not self.source_file:
            raise Exception('Please provide <source path>, <optional - destination path>.')
        try:
            self.data, self.file_type = get_dict_from_file(self.source_file, use_ryaml=True)
        except Exception:
            raise Exception(F'Provided file {self.source_file} is not a valid file.')
        self.from_version_key = self.set_from_version_key_name()

    def set_output_file_path(self, output_file_path) -> str:
        """Creates and format the output file name according to user input.
        Args:
            output_file_path: The output file name the user defined.
        Returns:
            str. the full formatted output file name.
        """
        if not output_file_path:
            source_dir = os.path.dirname(self.source_file)
            file_name = os.path.basename(self.source_file)
            if self.__class__.__name__ == 'PlaybookYMLFormat':
                if "Pack" not in source_dir:
                    if not file_name.startswith('playbook-'):
                        file_name = F'playbook-{file_name}'

            return os.path.join(source_dir, file_name)
        else:
            return output_file_path

    def set_version_to_default(self, location=None):
        """Replaces the version of the YML to default."""
        print(F'Setting JSON version to default: {DEFAULT_VERSION}')
        if location:
            location['version'] = DEFAULT_VERSION
        else:
            self.data['version'] = DEFAULT_VERSION

    def remove_unnecessary_keys(self):
        """Removes keys that are in file but not in schema of file type"""
        arguments_to_remove = self.arguments_to_remove()
        for key in arguments_to_remove:
            print(F'Removing Unnecessary fields {key} from file')
            self.data.pop(key, None)

    def set_fromVersion(self, from_version=None):
        """Sets fromversion key in file:
        Args:
            from_version: The specific from_version value.
        """
        # If there is no existing file in content repo
        if not self.old_file:
            print('Setting fromVersion field')
            # If current file does not have fromversion key
            if self.from_version_key not in self.data:

                # If user entered specific from version key to be set
                if from_version:
                    self.data[self.from_version_key] = from_version

                # Otherwise add fromversion key to current file and set to default 5.0.0
                else:
                    self.data[self.from_version_key] = NEW_FILE_DEFAULT_5_FROMVERSION

        # If there is an existing file in content repo
        else:
            # If current file does not have fromversion key
            if self.from_version_key not in self.data:

                # If user entered specific from version key to be set
                if from_version:
                    self.data[self.from_version_key] = from_version

                # If existing file already have a fromversion key, copy its value to current file
                elif self.from_version_key in self.old_file:
                    self.data[self.from_version_key] = self.old_file[self.from_version_key]

                # Otherwise add fromversion key to current file and set to default 1.0.0
                else:
                    self.data[self.from_version_key] = OLD_FILE_DEFAULT_1_FROMVERSION

    def arguments_to_remove(self) -> List[str]:
        """ Finds diff between keys in file and schema of file type
        Returns:
            List of keys that should be deleted in file
        """
        arguments_to_remove = []
        with open(self.schema_path, 'r') as file_obj:
            a = yaml.safe_load(file_obj)
        schema_fields = a.get('mapping').keys()
        file_fields = self.data.keys()
        for field in file_fields:
            if field not in schema_fields:
                arguments_to_remove.append(field)
        return arguments_to_remove

    def set_from_version_key_name(self) -> Union[str, None]:
        """fromversion key is different between yml and json , in yml file : fromversion, in json files : fromVersion"""
        if self.file_type == "yml":
            return 'fromversion'
        elif self.file_type == "json":
            return 'fromVersion'
        return None

    def is_old_file(self, path: str) -> dict:
        """Check whether the file is in git repo or new file.  """
        if path:
            data = get_remote_file(path)
            if not data:
                return {}
            else:
                return data
        return {}

    def remove_copy_and_dev_suffixes_from_name(self):
        """Removes any _dev and _copy suffixes in the file.
        When developer clones playbook/integration/script it will automatically add _copy or _dev suffix.
        """
        print('Removing _dev and _copy suffixes from name and display tags')
        if self.data['name']:
            self.data['name'] = self.data.get('name', '').replace('_copy', '').replace('_dev', '')
        if self.data.get('display'):
            self.data['display'] = self.data.get('display', '').replace('_copy', '').replace('_dev', '')

    def initiate_file_validator(self, validator_type):
        """ Run schema validate and file validate of file
        Returns:
            int 0 in case of success
            int 1 in case of error
            int 2 in case of skip
        """
        if self.no_validate:
            print_color(f'Validator Skipped on file: {self.output_file} , no-validate flag was set.',
                        LOG_COLORS.YELLOW)
            return SKIP_RETURN_CODE
        else:
            print_color('Starting validating files structure', LOG_COLORS.GREEN)
            if self.relative_content_path:
                structure_validator = StructureValidator(self.relative_content_path)
                validator = validator_type(structure_validator)
                if structure_validator.is_valid_file() and validator.is_valid_file(validate_rn=False):
                    print_color('The files are valid', LOG_COLORS.GREEN)
                    return SUCCESS_RETURN_CODE
                else:
                    print_color('The files are invalid', LOG_COLORS.RED)
                    return ERROR_RETURN_CODE
            else:
                print_color(f'The file {self.output_file} are not part of content repo, Validator Skipped',
                            LOG_COLORS.YELLOW)
                return SKIP_RETURN_CODE
