import os
import re
from copy import deepcopy
from typing import Any, Dict, Set, Union

import click
import dictdiffer

from demisto_sdk.commands.common.constants import GENERAL_DEFAULT_FROMVERSION, VERSION_5_5_0
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_dict_from_file, get_max_version, get_remote_file,
                                               is_file_from_content_repo)
from demisto_sdk.commands.format.format_constants import (DEFAULT_VERSION, ERROR_RETURN_CODE,
                                                          JSON_FROM_SERVER_VERSION_KEY, OLD_FILE_TYPES,
                                                          SKIP_RETURN_CODE, SUCCESS_RETURN_CODE)
from demisto_sdk.commands.validate.validate_manager import ValidateManager

yaml = YAML_Handler(allow_duplicate_keys=True)


class BaseUpdate:
    """BaseUpdate is the base class for all format commands.
        Attributes:
            source_file (str): the path to the file we are updating at the moment.
            output_file (str): the desired file name to save the updated version of the YML to.
            relative_content_path (str): Relative content path of output path.
            old_file (dict): Data of old file from content repo, if exist.
            schema_path (str): Schema path of file.
            from_version (str): Value of Wanted fromVersion key in file.
            prev_ver (str): Against which branch to perform diff
            data (dict): Dictionary of loaded file.
            file_type (str): Whether the file is yml or json.
            from_version_key (str): The fromVersion key in file, different between yml and json files.
            verbose (bool): Whether to print a verbose log
            assume_yes (bool): Whether to assume "yes" as answer to all prompts and run non-interactively
            interactive (bool): Whether to run the format interactively or not (usually for contribution management)
    """

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 prev_ver: str = 'master',
                 no_validate: bool = False,
                 verbose: bool = False,
                 assume_yes: bool = False,
                 interactive: bool = True,
                 clear_cache: bool = False,
                 **kwargs):
        self.source_file = input
        self.output_file = self.set_output_file_path(output)
        self.verbose = verbose
        _, self.relative_content_path = is_file_from_content_repo(self.output_file)
        self.prev_ver = prev_ver
        self.old_file = self.is_old_file(self.relative_content_path if self.relative_content_path
                                         else self.output_file, self.prev_ver, self.verbose)
        self.schema_path = path
        self.from_version = from_version
        self.no_validate = no_validate
        self.assume_yes = assume_yes
        self.interactive = interactive
        self.updated_ids: Dict = {}
        if not self.no_validate:
            self.validate_manager = ValidateManager(silence_init_prints=True, skip_conf_json=True,
                                                    skip_dependencies=True, skip_pack_rn_validation=True,
                                                    check_is_unskipped=False, validate_id_set=False)

        if not self.source_file:
            raise Exception('Please provide <source path>, <optional - destination path>.')
        try:
            self.data, self.file_type = get_dict_from_file(self.source_file, clear_cache=clear_cache)
        except Exception:
            raise Exception(F'Provided file {self.source_file} is not a valid file.')
        self.from_version_key = self.set_from_version_key_name()
        self.json_from_server_version_key = JSON_FROM_SERVER_VERSION_KEY
        self.id_set_file, _ = get_dict_from_file(path=kwargs.get('id_set_path'))  # type: ignore[arg-type]

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
        self.set_default_value('version', DEFAULT_VERSION, location)

    def set_default_value(self, key: str, value: Any, location=None):
        """Replaces the version to default."""
        if self.verbose:
            click.echo(f'Setting {key} to default={value}' +
                       ' in custom location' if location else '')
        if location:
            location[key] = value
        else:
            self.data[key] = value

    def remove_unnecessary_keys(self):
        """Removes keys that are in file but not in schema of file type"""
        with open(self.schema_path, 'r') as file_obj:
            schema = yaml.load(file_obj)
            extended_schema = self.recursive_extend_schema(schema, schema)
        if self.verbose:
            print('Removing Unnecessary fields from file')
        if isinstance(extended_schema, dict):
            self.recursive_remove_unnecessary_keys(extended_schema.get('mapping', {}), self.data)

    @staticmethod
    def recursive_extend_schema(current_schema: Union[str, bool, list, dict],
                                full_schema: dict) -> Union[str, bool, list, dict]:
        """
        Parses partial schemas into one schema.
        Removing the `schema;(schema-name)` and include syntax.
        See here for more info https://pykwalify.readthedocs.io/en/unstable/partial-schemas.html#schema-schema-name.

        This method recursively returns the unified scheme
        Args:
            current_schema: The current analyzed recursive schema
            full_schema: The original schema

        Returns:
            The unified schema with out the `schema;(schema-name)` and include syntax.
        """
        # This is the base condition, if the current schema is str or bool we can safely return it.
        if isinstance(current_schema, str) or isinstance(current_schema, bool):
            return current_schema
        # If the current schema is a list - we will return the extended schema of each of it's elements
        if isinstance(current_schema, list):
            return [BaseUpdate.recursive_extend_schema(value, full_schema) for value in current_schema]
        # If the current schema is a dict this is the main condition we will handle
        if isinstance(current_schema, dict):
            modified_schema = {}
            for key, value in current_schema.items():
                # There is no need to add the sub-schemas themselves, as we want to drop them
                if key.startswith('schema;'):
                    continue
                # If this is a reference to a sub-schema - we will replace the reference with the original.
                if isinstance(value, str) and key == 'include':
                    extended_schema: dict = full_schema.get(f'schema;{value}')  # type: ignore
                    if extended_schema is None:
                        click.echo(f"Could not find sub-schema for {value}", LOG_COLORS.YELLOW)
                    # sometimes the sub-schema can have it's own sub-schemas so we need to unify that too
                    return BaseUpdate.recursive_extend_schema(deepcopy(extended_schema), full_schema)
                else:
                    # This is the mapping case in which we can let the recursive method do it's thing on the values
                    modified_schema[key] = BaseUpdate.recursive_extend_schema(value, full_schema)
            return modified_schema

    def recursive_remove_unnecessary_keys(self, schema: dict, data: dict) -> None:
        """Recursively removes all the unnecessary fields in the file

        Args:
            schema: The schema with which we can check if a field should be removed
            data: The actual data of the file from which we will want to remove the fields.
        """
        data_fields = set(data.keys())
        for field in data_fields:
            if field not in schema.keys():
                # check if one of the schema keys is a regex that matches the data field - for example refer to the
                # tasks key in playbook.yml schema where a field should match the regex (^[0-9]+$)
                matching_key = self.regex_matching_key(field, schema.keys())
                if matching_key:
                    mapping = schema.get(matching_key, {}).get('mapping')
                    if mapping:
                        self.recursive_remove_unnecessary_keys(
                            schema.get(matching_key, {}).get('mapping'),
                            data.get(field, {})
                        )
                else:
                    if self.verbose:
                        print(f'Removing {field} field')
                    data.pop(field, None)
            else:
                mapping = schema.get(field, {}).get('mapping')
                if mapping:  # type: ignore
                    self.recursive_remove_unnecessary_keys(
                        schema.get(field, {}).get('mapping'),
                        data.get(field, {})
                    )
                # In case he have a sequence with mapping key in it's first element it's a continuation of the schema
                # and we need to remove unnecessary keys from it too.
                # In any other case there is nothing to do with the sequence
                else:
                    sequence = schema.get(field, {}).get('sequence', [])
                    if sequence and sequence[0].get('mapping'):
                        if data[field] is None:
                            if self.verbose:
                                print(f'Adding an empty array - `[]` as the value of the `{field}` field')
                            data[field] = []
                        else:
                            for list_element in data[field]:
                                self.recursive_remove_unnecessary_keys(
                                    sequence[0].get('mapping'),
                                    list_element
                                )

    def regex_matching_key(self, field, schema_keys):
        """
        Checks if the given data field matches a regex key in the schema.
        Args:
            field: the data field that should be matched.
            schema_keys: the keys in the schema that the data field should be checked against.

        Returns:
            the schema-key that is a regex which matches the given data field, if such a key exists, otherwise None.
        """
        regex_keys = [regex_key for regex_key in schema_keys if 'regex;' in regex_key]
        for reg in regex_keys:
            if re.match(reg.split(';')[1], field):
                return reg
        return None

    @staticmethod
    def get_answer(promote):
        click.secho(promote, fg='red')
        return input()

    def ask_user(self, preserve_from_version_question=False):
        if preserve_from_version_question:
            user_answer = self.get_answer(
                f'Both "{self.from_version_key}" and "{self.json_from_server_version_key}" '
                'entries were found with different values. '
                f'Would you like to preserve the value of the "{self.from_version_key}" entry? [Y/n]')
        else:
            user_answer = self.get_answer(
                'Either no fromversion is specified in your file, '
                'or it is lower than the minimal fromversion for this content type.'
                'Would you like to set it to the default? [Y/n]')
        if not user_answer or user_answer.lower() in ['y', 'yes']:
            return True
        else:
            click.secho('Skipping update of fromVersion', fg='yellow')
            return False

    def set_default_from_version(self, default_from_version: str, current_fromversion_value: str, file_type: str):
        """
        Sets the default fromVersion key in the file:
            In case the user approved it:
                Set the fromversion to 5.0.0 for old content items.
                Set/update the fromversion to the input default if supplied.(checks if it is the highest one).
                In any other case set it to the general one.
        Args:
            default_from_version: default fromVersion specific to the content type.
            current_fromversion_value: current from_version if exists in the file.
            file_type: the file type.
        """
        max_version = get_max_version([GENERAL_DEFAULT_FROMVERSION, default_from_version, current_fromversion_value])
        if max_version != current_fromversion_value and (self.assume_yes or self.ask_user()):
            self.data[self.from_version_key] = max_version

    def set_fromVersion(self, default_from_version='', file_type: str = ''):
        """Sets fromVersion key in the file.
        Args:
            default_from_version: default fromVersion specific to the content type.
            file_type: the file type.
        """
        current_fromversion_value = self.data.get(self.from_version_key, '')
        if self.verbose:
            click.echo('Setting fromVersion field')

        if self.from_version:
            self.data[self.from_version_key] = self.from_version
        elif self.old_file.get(self.from_version_key):
            if not current_fromversion_value:
                self.data[self.from_version_key] = self.old_file.get(self.from_version_key)
        elif file_type and file_type in OLD_FILE_TYPES:
            self.data[self.from_version_key] = VERSION_5_5_0
        else:
            self.set_default_from_version(default_from_version, current_fromversion_value, file_type)

    def arguments_to_remove(self) -> Set[str]:
        """ Finds diff between keys in file and schema of file type.
        Returns:
            List of keys that should be deleted in file
        """
        with open(self.schema_path, 'r') as file_obj:
            a = yaml.load(file_obj)
        schema_fields = a.get('mapping').keys()
        arguments_to_remove = set(self.data.keys()) - set(schema_fields)
        return arguments_to_remove

    def set_from_version_key_name(self) -> Union[str, None]:
        """fromversion key is different between yml and json , in yml file : fromversion, in json files : fromVersion"""
        if self.file_type == "yml":
            return 'fromversion'
        elif self.file_type == "json":
            return 'fromVersion'
        return None

    @staticmethod
    def is_old_file(path: str, prev_ver: str, verbose: bool = False) -> dict:
        """Check whether the file is in git repo or new file.  """
        if path:
            data = get_remote_file(path, prev_ver, suppress_print=not verbose)
            if not data:
                return {}
            else:
                return data
        return {}

    def remove_copy_and_dev_suffixes_from_name(self):
        """Removes any _dev and _copy suffixes in the file.
        When developer clones playbook/integration/script it will automatically add _copy or _dev suffix.
        """
        if self.verbose:
            click.echo('Removing _dev and _copy suffixes from name, id and display tags')
        if self.data['name']:
            self.data['name'] = self.data.get('name', '').replace('_copy', '').replace('_dev', '')
        if self.data.get('display'):
            self.data['display'] = self.data.get('display', '').replace('_copy', '').replace('_dev', '')
        if self.data.get('id'):
            self.data['id'] = self.data.get('id', '').replace('_copy', '').replace('_dev', '')

    def initiate_file_validator(self) -> int:
        """ Run schema validate and file validate of file
        Returns:
            int 0 in case of success
            int 1 in case of error
            int 2 in case of skip
        """
        if self.no_validate:
            if self.verbose:
                click.secho(f'Validator Skipped on file: {self.output_file} , no-validate flag was set.', fg='yellow')
            return SKIP_RETURN_CODE
        else:
            self.validate_manager.file_path = self.output_file
            if self.is_old_file(self.output_file, self.prev_ver):
                validation_result = self.validate_manager.run_validation_using_git()
            else:
                validation_result = self.validate_manager.run_validation_on_specific_files()

            if not validation_result:
                return ERROR_RETURN_CODE

            else:
                return SUCCESS_RETURN_CODE

    def sync_data_to_master(self):
        if self.old_file:
            diff = dictdiffer.diff(self.old_file, self.data)
            self.data = dictdiffer.patch(diff, self.old_file)

    def check_server_version(self):
        """Checks for fromServerVersion entry in the file, and changeing it accordingly.
        """
        current_from_server_version = self.data.get(self.json_from_server_version_key)
        current_from_version = self.data.get(self.from_version_key)
        old_from_server_version = self.old_file.get(self.json_from_server_version_key)

        if old_from_server_version and not current_from_server_version and not current_from_version:
            self.data[self.from_version_key] = old_from_server_version
        elif current_from_server_version and not current_from_version:
            self.data[self.from_version_key] = current_from_server_version
            self.data.pop(self.json_from_server_version_key)
        elif current_from_server_version and current_from_version:
            if current_from_server_version == current_from_version:
                self.data.pop(self.json_from_server_version_key)
            else:
                preserve_from_version = self.ask_user(preserve_from_version_question=True)
                if preserve_from_version or self.assume_yes:
                    self.data.pop(self.json_from_server_version_key)
                else:
                    self.data[self.from_version_key] = current_from_server_version
                    self.data.pop(self.json_from_server_version_key)
