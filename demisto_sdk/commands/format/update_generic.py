import os
import re
from copy import deepcopy
from distutils.version import LooseVersion
from typing import Dict, Optional, Set, Union

import click
import yaml
from demisto_sdk.commands.common.constants import (INTEGRATION, PLAYBOOK,
                                                   FileType)
from demisto_sdk.commands.common.hook_validations.structure import \
    StructureValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, find_type,
                                               get_dict_from_file,
                                               get_pack_metadata,
                                               get_remote_file,
                                               is_file_from_content_repo,
                                               print_color)
from demisto_sdk.commands.format.format_constants import (
    DEFAULT_VERSION, ERROR_RETURN_CODE, NEW_FILE_DEFAULT_5_5_0_FROMVERSION,
    OLD_FILE_DEFAULT_1_FROMVERSION, SKIP_RETURN_CODE, SUCCESS_RETURN_CODE,
    VERSION_6_0_0)
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
            verbose (bool): Whether to print a verbose log
            assume_yes (bool): Whether to assume "yes" as answer to all prompts and run non-interactively
    """

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 assume_yes: bool = False,
                 deprecate: bool = False):
        self.source_file = input
        self.output_file = self.set_output_file_path(output)
        self.verbose = verbose
        _, self.relative_content_path = is_file_from_content_repo(self.output_file)
        self.old_file = self.is_old_file(self.relative_content_path if self.relative_content_path
                                         else self.output_file, self.verbose)
        self.schema_path = path
        self.from_version = from_version
        self.no_validate = no_validate
        self.assume_yes = assume_yes
        self.updated_id_dict: Dict = {}

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
        if self.verbose:
            click.echo(f'Setting JSON version to default: {DEFAULT_VERSION}')
        if location:
            location['version'] = DEFAULT_VERSION
        else:
            self.data['version'] = DEFAULT_VERSION

    def remove_unnecessary_keys(self):
        """Removes keys that are in file but not in schema of file type"""
        with open(self.schema_path, 'r') as file_obj:
            schema = yaml.safe_load(file_obj)
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

    def set_fromVersion(self, from_version=None, file_type: Optional[str] = None):
        """Sets fromversion key in file:
        Args:
            from_version: The specific from_version value.
            file_type: what is the file type: for now only integration type passed
        """
        metadata = get_pack_metadata(self.source_file)
        # if it is new contributed pack = setting version to 6.0.0
        should_set_from_version = ((metadata.get('currentVersion', '') == '1.0.0') and (metadata.get('support', '') != 'xsoar'))

        # If there is no existing file in content repo
        if not self.old_file:
            if self.verbose:
                click.echo('Setting fromVersion field')
            # If current file does not have fromversion key
            if self.from_version_key not in self.data:
                # If user entered specific from version key to be set
                if from_version:
                    self.data[self.from_version_key] = from_version
                # if it is new contributed pack = setting version to 6.0.0
                elif should_set_from_version:
                    self.data[self.from_version_key] = VERSION_6_0_0
                # Otherwise add fromversion key to current file and set to default 5.5.0
                else:
                    self.data[self.from_version_key] = NEW_FILE_DEFAULT_5_5_0_FROMVERSION
            # If user wants to modify fromversion key and the key already existed
            elif from_version:
                self.data[self.from_version_key] = from_version
            # if it is new contributed pack, this is integration, and its version is 5.5.0 do not change it
            # if it is new contributed pack = setting version to 6.0.0
            elif should_set_from_version:
                if self.data.get(self.from_version_key) != '5.5.0' or file_type != INTEGRATION:
                    self.data[self.from_version_key] = VERSION_6_0_0
            # If it is new pack, and it has from version lower than 5.5.0, ask to set it to 5.5.0
            # Playbook has its own validation in update_fromversion_by_user() function in update_playbook.py
            elif LooseVersion(self.data.get(self.from_version_key, '0.0.0')) < \
                    LooseVersion(NEW_FILE_DEFAULT_5_5_0_FROMVERSION) and file_type != PLAYBOOK:
                if self.assume_yes:
                    self.data[self.from_version_key] = NEW_FILE_DEFAULT_5_5_0_FROMVERSION
                else:
                    set_from_version = str(
                        input(f"\nYour current fromversion is: '{self.data.get(self.from_version_key)}'. Do you want "
                              f"to set it to '5.5.0'? Y/N ")).lower()
                    if set_from_version in ['y', 'yes']:
                        self.data[self.from_version_key] = NEW_FILE_DEFAULT_5_5_0_FROMVERSION

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

    def arguments_to_remove(self) -> Set[str]:
        """ Finds diff between keys in file and schema of file type
        Returns:
            List of keys that should be deleted in file
        """
        with open(self.schema_path, 'r') as file_obj:
            a = yaml.safe_load(file_obj)
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
    def is_old_file(path: str, verbose: bool = False) -> dict:
        """Check whether the file is in git repo or new file.  """
        if path:
            data = get_remote_file(path, suppress_print=not verbose)
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

    def initiate_file_validator(self, validator_type) -> int:
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
            if self.verbose:
                print_color('Starting validating files structure', LOG_COLORS.GREEN)
            # validates only on files in content repo
            if self.relative_content_path:
                file_type = find_type(self.output_file)

                # validates on the output file generated from the format
                structure_validator = StructureValidator(
                    self.output_file,
                    predefined_scheme=file_type,
                    suppress_print=not self.verbose
                )
                validator = validator_type(structure_validator, suppress_print=not self.verbose)

                # TODO: remove the connection condition if we implement a specific validator for connections.
                if structure_validator.is_valid_file() and \
                        (file_type in [FileType.CONNECTION, file_type == FileType.DESCRIPTION] or
                         validator.is_valid_file()):
                    if self.verbose:
                        click.secho('The files are valid', fg='green')
                    return SUCCESS_RETURN_CODE
                else:
                    if self.verbose:
                        click.secho('The files are invalid', fg='red')
                    return ERROR_RETURN_CODE
            else:
                if self.verbose:
                    click.secho(f'The file {self.output_file} are not part of content repo, Validator Skipped',
                                fg='yellow')
                return SKIP_RETURN_CODE
