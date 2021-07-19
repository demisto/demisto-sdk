import os
import re
from abc import ABC
from typing import Tuple

import click
import traceback
import yaml
from demisto_sdk.commands.common.hook_validations.pre_process_rules import PreProcessRulesValidator
from demisto_sdk.commands.common.tools import (LOG_COLORS, print_color,
                                               print_error)
from demisto_sdk.commands.format.format_constants import (
    DEFAULT_VERSION, ERROR_RETURN_CODE, NEW_FILE_DEFAULT_5_FROMVERSION,
    SKIP_RETURN_CODE, SUCCESS_RETURN_CODE, VERSION_6_0_0)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON

# LAYOUTS_CONTAINER_KINDS = ['edit',
#                            'indicatorsDetails',
#                            'indicatorsQuickView',
#                            'quickView',
#                            'close',
#                            'details',
#                            'detailsV2',
#                            'mobile']
PRE_PROCESS_RULES_KIND = 'preprocessrules'
# LAYOUTS_CONTAINER_PREFIX = 'layoutscontainer-'
PRE_PROCESS_RULES_PREFIX = 'preprocessrule-'


class PreProcessRulesBaseFormat(BaseUpdateJSON, ABC):

    def __init__(self,
                 input: str = '',
                 output: str = '',
                 path: str = 'pre-process-rules',
                 from_version: str = '',
                 no_validate: bool = False,
                 verbose: bool = False,
                 **kwargs):
        super().__init__(input=input, output=output, path=path, from_version=from_version, no_validate=no_validate,
                         verbose=verbose, **kwargs)

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the PreProcessRules JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator(PreProcessRulesValidator)

    def run_format(self) -> int:
        try:
            click.secho(f'\n======= Updating file: {self.source_file} =======', fg='white')
            self.pre_process_rules__run_format()
            # self.update_json()
            # FYI, self.update_json() is
            self.set_version_to_default()
            # self.remove_null_fields()
            self.remove_unnecessary_keys()
            # self.set_fromVersion(from_version=self.from_version)

            # self.set_description()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            print(''.join(traceback.format_exception(etype=type(exc), value=exc, tb=exc.__traceback__)))
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def arguments_to_remove(self):
        """ Finds diff between keys in file and schema of file type
        Returns:
            Tuple -
                Set of keys that should be deleted from file
                Dict with pre_process_rules kinds as keys and set of keys that should
                be deleted as values.
        """
        return self.pre_process_rules__arguments_to_remove()

    def pre_process_rules__run_format(self):
        """toVersion 5.9.9 layout format"""
        self.set_pre_process_rules_key()
        # version is both in pre_process_rules key and in base dict
        # self.set_version_to_default(self.data['version'])
        self.set_version_to_default()
        # self.set_toVersion()
        self.pre_process_rules__set_output_path()

    def pre_process_rules__set_output_path(self):
        output_basename = os.path.basename(self.output_file)
        if not output_basename.startswith(PRE_PROCESS_RULES_PREFIX):
            new_output_basename = PRE_PROCESS_RULES_PREFIX
            new_output_path = self.output_file.replace(output_basename, new_output_basename)

            # rename file if source and output are the same
            if self.output_file == self.source_file:
                os.rename(self.source_file, new_output_path)
                self.source_file = new_output_path

            self.output_file = new_output_path

    # def layoutscontainer__run_format(self) -> None:
    #     """fromVersion 6.0.0 layout (container) format"""
    #     self.set_fromVersion(from_version=VERSION_6_0_0)
    #     self.set_group_field()
    #     self.layoutscontainer__set_output_path()
    #     self.update_id(field='name')

    # def layoutscontainer__set_output_path(self):
    #     output_basename = os.path.basename(self.output_file)
    #     if not output_basename.startswith(LAYOUTS_CONTAINER_PREFIX):
    #         new_output_basename = LAYOUTS_CONTAINER_PREFIX + output_basename.split(LAYOUT_PREFIX)[-1]
    #         new_output_path = self.output_file.replace(output_basename, new_output_basename)

    #         # rename file if source and output are the same
    #         if self.output_file == self.source_file:
    #             os.rename(self.source_file, new_output_path)
    #             self.source_file = new_output_path

    #         self.output_file = new_output_path

    def remove_unnecessary_keys(self):
        """Removes keys that are in file but not in schema of file type"""
        arguments_to_remove, pre_process_rules_kind_args_to_remove = self.arguments_to_remove()
        for key in arguments_to_remove:
            if self.verbose:
                click.echo(F'Removing unnecessary field: {key} from file')
            self.data.pop(key, None)

        for kind in pre_process_rules_kind_args_to_remove:
            if self.verbose:
                click.echo(F'Removing unnecessary fields from {kind} field')
            for field in pre_process_rules_kind_args_to_remove[kind]:
                self.data[kind].pop(field, None)

    def set_pre_process_rules_key(self):
        # TODO Needed?
        # if "pre_process_rules" not in self.data.keys():
        #     # kind = self.data['kind']
        #     # id = self.data['id']
        #     self.data = {
        #         # "typeId": id,
        #         "version": DEFAULT_VERSION,
        #         # "TypeName": id,
        #         # "kind": kind,
        #         # TODO fromServerVersion?
        #         # "fromVersion": NEW_FILE_DEFAULT_5_FROMVERSION,
        #         # "layout": self.data
        #     }
        pass

    def set_group_field(self):
        if self.data['group'] != 'incident' and self.data['group'] != 'indicator':
            click.secho('No group is specified for this pre_process_rules, would you like me to update for you? [Y/n]',
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

    def pre_process_rules__arguments_to_remove(self):
        """ Finds diff between keys in file and schema of file type
        Returns:
            Tuple -
                Set of keys that should be deleted from file
                Dict with pre_process_rules kinds as keys and set of keys that should
                be deleted as values.
        """
        with open(self.schema_path, 'r') as file_obj:
            a = yaml.safe_load(file_obj)
        schema_fields = a.get('mapping').keys()
        first_level_args = set(self.data.keys()) - set(schema_fields)

        # TODO Needed?
        # second_level_args = {}
        # kind_schema = a['mapping'][PRE_PROCESS_RULES_KIND]['mapping'].keys()
        # second_level_args[PRE_PROCESS_RULES_KIND] = set(self.data[PRE_PROCESS_RULES_KIND].keys()) - set(kind_schema)

        # return first_level_args, second_level_args
        return first_level_args, {}

    # def layoutscontainer__arguments_to_remove(self):
    #     """ Finds diff between keys in file and schema of file type
    #     Returns:
    #         Tuple -
    #             Set of keys that should be deleted from file
    #             Dict with layout kinds as keys and set of keys that should
    #             be deleted as values.
    #     """
    #     with open(self.schema_path, 'r') as file_obj:
    #         a = yaml.safe_load(file_obj)
    #     schema_fields = a.get('mapping').keys()
    #     first_level_args = set(self.data.keys()) - set(schema_fields)

    #     second_level_args = {}
    #     for kind in LAYOUTS_CONTAINER_KINDS:
    #         if kind in self.data:
    #             kind_schema = a['mapping'][kind]['mapping'].keys()
    #             second_level_args[kind] = set(self.data[kind].keys()) - set(kind_schema)

    #     return first_level_args, second_level_args
