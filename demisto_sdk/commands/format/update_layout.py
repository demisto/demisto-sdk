import re
from abc import ABC
from typing import Tuple

import yaml
from demisto_sdk.commands.common.hook_validations.layout import LayoutValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)
from demisto_sdk.commands.format.format_constants import (
    DEFAULT_VERSION, ERROR_RETURN_CODE, NEW_FILE_DEFAULT_5_FROMVERSION,
    SKIP_RETURN_CODE, SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

LAYOUTS_CONTAINER_FROM_VERSION = '6.0.0'
LAYOUTS_CONTAINER_KINDS = ['edit',
                           'indicatorsDetails',
                           'indicatorsQuickView',
                           'quickView',
                           'close',
                           'details',
                           'detailsV2',
                           'mobile']
LAYOUT_KIND = 'layout'


class LayoutBaseFormat(BaseUpdateJSON, ABC):

    def __init__(self, input: str = '', output: str = '', path: str = '', from_version: str = '',
                 no_validate: bool = False):
        super().__init__(input, output, path, from_version, no_validate)

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the integration YML updater."""
        format = self.run_format()
        if format:
            return format, SKIP_RETURN_CODE
        else:
            return format, self.initiate_file_validator(LayoutValidator)

    def set_description(self):
        """Add empty description to file root."""
        if 'description' not in self.data:
            print('Adding empty descriptions to root')
            self.data['description'] = ''

    def remove_unnecessary_keys(self):
        """Removes keys that are in file but not in schema of file type"""
        arguments_to_remove, layout_kind_args_to_remove = self.arguments_to_remove()
        for key in arguments_to_remove:
            print(F'Removing unnecessary field: {key} from file')
            self.data.pop(key, None)
        for kind in layout_kind_args_to_remove:
            print(F'Removing unnecessary fields from {kind} field')
            for field in layout_kind_args_to_remove[kind]:
                self.data[kind].pop(field, None)

    def run_format(self):
        self.set_description()
        self.set_version_to_default()
        self.save_json_to_destination_file()


class LayoutJSONFormat(LayoutBaseFormat):
    """LayoutJSONFormat class is designed to update layout JSON file according to Demisto's convention.

        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
    """

    def run_format(self) -> int:
        try:
            print_color(F'\n=======Starting updates for file: {self.source_file}=======', LOG_COLORS.WHITE)
            self.set_layout_key()
            # version is both in layout key and in base dict
            self.set_version_to_default(self.data['layout'])
            self.set_fromVersion(from_version=self.from_version)
            self.set_toVersion()
            self.remove_unnecessary_keys()
            super().run_format()

            print_color(F'=======Finished updates for files: {self.output_file}=======\n', LOG_COLORS.WHITE)
            return SUCCESS_RETURN_CODE
        except Exception:
            return ERROR_RETURN_CODE

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

    def arguments_to_remove(self):
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


class LayoutsContainerJSONFormat(LayoutBaseFormat):
    def run_format(self) -> int:
        try:
            print_color(F'\n=======Starting updates for file: {self.source_file}=======', LOG_COLORS.WHITE)
            self.remove_null_kinds()
            self.set_fromVersion(from_version=LAYOUTS_CONTAINER_FROM_VERSION)
            self.set_group_field()
            self.remove_unnecessary_keys()
            super().run_format()

            print_color(F'=======Finished updates for files: {self.output_file}=======\n', LOG_COLORS.WHITE)
            return SUCCESS_RETURN_CODE
        except Exception:
            return ERROR_RETURN_CODE

    def set_group_field(self):
        if self.data['group'] != 'incident' and self.data['group'] != 'indicator':
            print_color('No group is specified for this layout, would you like me to update for you? [Y/n]',
                        LOG_COLORS.RED)
            user_answer = input()
            # Checks if the user input is no
            if user_answer in ['n', 'N', 'No', 'no']:
                print_error('Moving forward without updating group field')
                return

            print_color('Please specify the desired group: incident or indicator', LOG_COLORS.YELLOW)
            user_desired_version = input()
            if re.match(r'(^incident$)', user_desired_version, re.IGNORECASE):
                self.data['group'] = 'incident'
            elif re.match(r'(^indicator$)', user_desired_version, re.IGNORECASE):
                self.data['group'] = 'indicator'
            else:
                print_error('Group is not valid')

    def remove_null_kinds(self):
        """
        Remove layout kinds with null as value.
        Layoutscontainer file which was downloaded from server contains all layouts kinds.
        layout kinds:
                edit,
                indicatorsDetails,
                indicatorsQuickView,
                quickView,
                close,
                details,
                detailsV2,
                mobile
        """
        for kind in LAYOUTS_CONTAINER_KINDS:
            if not self.data.get(kind):
                self.data.pop(kind)

    def arguments_to_remove(self):
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
