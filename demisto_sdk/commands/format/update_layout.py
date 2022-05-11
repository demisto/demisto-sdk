import os
import re
from abc import ABC
from typing import Tuple

import click

from demisto_sdk.commands.common.constants import (
    FileType,
    LAYOUT_AND_MAPPER_BUILT_IN_FIELDS
)
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.tools import (
    LOG_COLORS, print_color, print_error,
    remove_copy_and_dev_suffixes_from_str,
    get_all_incident_and_indicator_fields_from_id_set, LAYOUT_CONTAINER_FIELDS
)
from demisto_sdk.commands.format.format_constants import (
    DEFAULT_VERSION, ERROR_RETURN_CODE, NEW_FILE_DEFAULT_5_FROMVERSION,
    SKIP_RETURN_CODE, SUCCESS_RETURN_CODE, VERSION_6_0_0)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON
from demisto_sdk.commands.common.update_id_set import BUILT_IN_FIELDS

yaml = YAML_Handler()

SCRIPT_QUERY_TYPE = 'script'

LAYOUTS_CONTAINER_KINDS = ['edit',
                           'indicatorsDetails',
                           'indicatorsQuickView',
                           'quickView',
                           'close',
                           'details',
                           'detailsV2',
                           'mobile']

LAYOUTS_CONTAINER_CHECK_SCRIPTS = ('indicatorsDetails', 'detailsV2')

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
                 clear_cache: bool = False,
                 **kwargs):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
                         verbose=verbose, clear_cache=clear_cache, **kwargs)

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
        self.update_json(file_type=FileType.LAYOUT.value)
        self.set_layout_key()
        # version is both in layout key and in base dict
        self.set_version_to_default(self.data['layout'])
        self.set_toVersion()
        self.layout__set_output_path()
        self.remove_copy_and_dev_suffixes_from_layout()
        self.remove_inexistent_fields_layout()

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
        super().update_json(default_from_version=VERSION_6_0_0)
        self.set_group_field()
        self.layoutscontainer__set_output_path()
        self.update_id(field='name')
        self.remove_copy_and_dev_suffixes_from_layoutscontainer()
        self.remove_inexistent_fields_layoutscontainer()

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
            a = yaml.load(file_obj)
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
            a = yaml.load(file_obj)
        schema_fields = a.get('mapping').keys()
        first_level_args = set(self.data.keys()) - set(schema_fields)

        second_level_args = {}
        for kind in LAYOUTS_CONTAINER_KINDS:
            if kind in self.data:
                kind_schema = a['mapping'][kind]['mapping'].keys()
                second_level_args[kind] = set(self.data[kind].keys()) - set(kind_schema)

        return first_level_args, second_level_args

    def remove_copy_and_dev_suffixes_from_layoutscontainer(self):
        if name := self.data.get('name'):
            self.data['name'] = remove_copy_and_dev_suffixes_from_str(name)

        container = None
        for kind in LAYOUTS_CONTAINER_CHECK_SCRIPTS:
            if self.data.get(kind):
                container = self.data.get(kind)
                break
        if container:
            for tab in container.get('tabs', ()):
                for section in tab.get('sections', ()):
                    if section.get('queryType') == SCRIPT_QUERY_TYPE:
                        section['query'] = remove_copy_and_dev_suffixes_from_str(section.get('query'))
                        section['name'] = remove_copy_and_dev_suffixes_from_str(section.get('name'))

    def remove_copy_and_dev_suffixes_from_layout(self):
        if typename := self.data.get('TypeName'):
            self.data['TypeName'] = remove_copy_and_dev_suffixes_from_str(typename)
        if type_id := self.data.get('typeId'):
            self.data['typeId'] = remove_copy_and_dev_suffixes_from_str(type_id)

        if layout_data := self.data.get('layout'):
            if layout_tabs := layout_data.get('tabs', ()):
                for tab in layout_tabs:
                    for section in tab.get('sections', ()):
                        if section.get('queryType') == SCRIPT_QUERY_TYPE:
                            section['query'] = remove_copy_and_dev_suffixes_from_str(section.get('query'))
                            section['name'] = remove_copy_and_dev_suffixes_from_str(section.get('name'))

            elif layout_sections := layout_data.get('sections'):
                for section in layout_sections:
                    if section.get('queryType') == SCRIPT_QUERY_TYPE:
                        section['query'] = remove_copy_and_dev_suffixes_from_str(section.get('query'))
                        section['name'] = remove_copy_and_dev_suffixes_from_str(section.get('name'))

    def remove_inexistent_fields_layoutscontainer(self):
        """
        Remove in-existent incident/indicator fields from a container layout.
        """
        if not self.id_set_file:
            return

        content_fields = get_all_incident_and_indicator_fields_from_id_set(self.id_set_file, 'layout')
        built_in_fields = [field.lower() for field in BUILT_IN_FIELDS] + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS

        layout_container_items = [
            layout_container_field for layout_container_field in LAYOUT_CONTAINER_FIELDS
            if self.data.get(layout_container_field)
        ]

        for layout_container_item in layout_container_items:
            layout = self.data.get(layout_container_item, {})
            layout_tabs = layout.get('tabs', [])
            self.remove_inexistent_fields_from_tabs(
                layout_tabs=layout_tabs, content_fields=content_fields, built_in_fields=built_in_fields
            )

    @staticmethod
    def extract_content_fields(content_fields, built_in_fields):
        """
        Get only incident/indicator fields which are part of the id json file.
        """
        def _extract_content_fields(field):
            """
            Get only incident/indicator fields which are part of the id json file.
            """
            field = field.get('fieldId', '').replace('incident_', '').replace('indicator_', '').lower()
            return field in built_in_fields or field in content_fields

        return _extract_content_fields

    def remove_inexistent_fields_from_tabs(self, layout_tabs, content_fields, built_in_fields):
        """
        Remove in-existent fields which are not part of the id json from tabs.
        """
        for tab in layout_tabs:
            layout_sections = tab.get('sections', [])
            for section in layout_sections:
                items = section.get('items', [])
                section['items'] = list(
                    filter(
                        self.extract_content_fields(content_fields=content_fields, built_in_fields=built_in_fields),
                        items
                    )
                )

    def remove_inexistent_fields_layout(self):
        """
        Remove in-existent fields from a layout.
        """
        if not self.id_set_file:
            return

        content_fields = get_all_incident_and_indicator_fields_from_id_set(self.id_set_file, 'layout')
        built_in_fields = [field.lower() for field in BUILT_IN_FIELDS] + LAYOUT_AND_MAPPER_BUILT_IN_FIELDS

        layout = self.data.get('layout', {})
        layout_sections = layout.get('sections', [])
        for section in layout_sections:
            fields = section.get('fields', [])
            section['fields'] = list(
                filter(
                    self.extract_content_fields(content_fields=content_fields, built_in_fields=built_in_fields),
                    fields
                )
            )

        self.remove_inexistent_fields_from_tabs(
            layout_tabs=layout.get('tabs', []), content_fields=content_fields, built_in_fields=built_in_fields
        )
