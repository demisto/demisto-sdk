import os
import re
from abc import ABC
from typing import Tuple

import click
import yaml

from demisto_sdk.commands.common.constants import OLDEST_SUPPORTED_VERSION
from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)
from demisto_sdk.commands.format.format_constants import (
    DEFAULT_VERSION, ERROR_RETURN_CODE, NEW_FILE_DEFAULT_5_FROMVERSION,
    SKIP_RETURN_CODE, SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

LAYOUTS_CONTAINER_KINDS = ['edit',
                           'indicatorsDetails',
                           'indicatorsQuickView',
                           'quickView',
                           'close',
                           'details',
                           'detailsV2',
                           'mobile']
LAYOUT_KIND = 'layout'
LAYOUTS_CONTAINER_PREFIX = 'layoutscontainer-'
LAYOUT_PREFIX = 'layout-'


class LayoutBaseFormat(BaseUpdateJSON, ABC):

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = '',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
                         verbose=verbose, **kwargs)

        # layoutscontainer kinds are unique fields to containers, and shouldn't be in layouts
        self.is_container = any(self.data.get(kind) for kind in LAYOUTS_CONTAINER_KINDS)

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the Layout JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator()

    def run_format(self) -> int:
        try:
            click.secho(f'\n================= Updating file {self.source_file} =================', fg='bright_blue')
            if self.is_container:
                self.layoutscontainer__run_format()
            else:
                self.layout__run_format()
            self.update_json()
            self.set_description()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def arguments_to_remove(self):
        """ Finds diff between keys in file and schema of file type
        Returns:
            Tuple -
                Set of keys that should be deleted from file
                Dict with layout kinds as keys and set of keys that should
                be deleted as values.
        """
        if self.is_container:
            return self.layoutscontainer__arguments_to_remove()
        return self.layout__arguments_to_remove()

    def layout__run_format(self):
        """toVersion 5.9.9 layout format"""
        self.set_layout_key()
        # version is both in layout key and in base dict
        self.set_version_to_default(self.data['layout'])
        self.set_toVersion()
        self.layout__set_output_path()

    def layout__set_output_path(self):
        output_basename = os.path.basename(self.output_file)
        if not output_basename.startswith(LAYOUT_PREFIX):
            new_output_basename = LAYOUT_PREFIX + output_basename.split(LAYOUTS_CONTAINER_PREFIX)[-1]
            new_output_path = self.output_file.replace(output_basename, new_output_basename)

            # rename file if source and output are the same
            if self.output_file == self.source_file:
                os.rename(self.source_file, new_output_path)
                self.source_file = new_output_path

            self.output_file = new_output_path

    def layoutscontainer__run_format(self) -> None:
        """fromVersion 6.0.0 layout (container) format"""
        self.set_fromVersion(from_version=OLDEST_SUPPORTED_VERSION)
        self.set_group_field()
        self.layoutscontainer__set_output_path()
        self.update_id(field='name')

    def layoutscontainer__set_output_path(self):
        output_basename = os.path.basename(self.output_file)
        if not output_basename.startswith(LAYOUTS_CONTAINER_PREFIX):
            new_output_basename = LAYOUTS_CONTAINER_PREFIX + output_basename.split(LAYOUT_PREFIX)[-1]
            new_output_path = self.output_file.replace(output_basename, new_output_basename)

            if self.verbose:
                click.echo(f"Renaming output file: {new_output_path}")

            # rename file if source and output are the same
            if self.output_file == self.source_file:
                os.rename(self.source_file, new_output_path)
                self.source_file = new_output_path

            self.output_file = new_output_path

    def remove_unnecessary_keys(self):
        """Removes keys that are in file but not in schema of file type"""
        arguments_to_remove, layout_kind_args_to_remove = self.arguments_to_remove()
        for key in arguments_to_remove:
            if self.verbose:
                click.echo(F'Removing unnecessary field: {key} from file')
            self.data.pop(key, None)

        for kind in layout_kind_args_to_remove:
            if self.verbose:
                click.echo(F'Removing unnecessary fields from {kind} field')
            for field in layout_kind_args_to_remove[kind]:
                self.data[kind].pop(field, None)

    def set_layout_key(self):
        if "layout" not in self.data.keys():
            kind = self.data['kind']
            id = self.data['id']
            self.data = {
                "typeId": id,
                "version": DEFAULT_VERSION,
                "TypeName": id,
                "kind": kind,
                "fromVersion": NEW_FILE_DEFAULT_5_FROMVERSION,
                "layout": self.data
            }

    def set_group_field(self):
        if self.data['group'] != 'incident' and self.data['group'] != 'indicator':
            click.secho('No group is specified for this layout, would you like me to update for you? [Y/n]',
                        fg='red')
            user_answer = input()
            # Checks if the user input is no
            if user_answer in ['n', 'N', 'No', 'no']:
                print_error('Moving forward without updating group field')
                return

            print_color('Please specify the desired group: incident or indicator', LOG_COLORS.YELLOW)
            user_desired_group = input()
            if re.match(r'(^incident$)', user_desired_group, re.IGNORECASE):
                self.data['group'] = 'incident'
            elif re.match(r'(^indicator$)', user_desired_group, re.IGNORECASE):
                self.data['group'] = 'indicator'
            else:
                print_error('Group is not valid')

    def layout__arguments_to_remove(self):
        """ Finds diff between keys in file and schema of file type
        Returns:
            Tuple -
                Set of keys that should be deleted from file
                Dict with layout kinds as keys and set of keys that should
                be deleted as values.
        """
        with open(self.schema_path, 'r') as file_obj:
            a = yaml.safe_load(file_obj)
        schema_fields = a.get('mapping').keys()
        first_level_args = set(self.data.keys()) - set(schema_fields)

        second_level_args = {}
        kind_schema = a['mapping'][LAYOUT_KIND]['mapping'].keys()
        second_level_args[LAYOUT_KIND] = set(self.data[LAYOUT_KIND].keys()) - set(kind_schema)

        return first_level_args, second_level_args

    def layoutscontainer__arguments_to_remove(self):
        """ Finds diff between keys in file and schema of file type
        Returns:
            Tuple -
                Set of keys that should be deleted from file
                Dict with layout kinds as keys and set of keys that should
                be deleted as values.
        """
        with open(self.schema_path, 'r') as file_obj:
            a = yaml.safe_load(file_obj)
        schema_fields = a.get('mapping').keys()
        first_level_args = set(self.data.keys()) - set(schema_fields)

        second_level_args = {}
        for kind in LAYOUTS_CONTAINER_KINDS:
            if kind in self.data:
                kind_schema = a['mapping'][kind]['mapping'].keys()
                second_level_args[kind] = set(self.data[kind].keys()) - set(kind_schema)

        return first_level_args, second_level_args
