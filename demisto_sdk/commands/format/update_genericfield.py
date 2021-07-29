from typing import Tuple

import click

from demisto_sdk.commands.common.hook_validations.generic_field import \
    GenericFieldValidator
from demisto_sdk.commands.format.format_constants import (
    ERROR_RETURN_CODE, GENERIC_FIELD_DEFAULT_GROUP,
    GENERIC_FIELD_DEFAULT_ID_PREFIX, SKIP_RETURN_CODE, SUCCESS_RETURN_CODE)
from demisto_sdk.commands.format.update_generic_json import BaseUpdateJSON


class GenericFieldJSONFormat(BaseUpdateJSON):
    """GenericFieldJSONFormat class is designed to update generic field JSON file according to Demisto's
     convention.

       Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the JSON to.
    """

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

    def run_format(self) -> int:
        try:
            click.secho(f'\n======= Updating file: {self.source_file} =======', fg='white')
            super().update_json()
            self.set_default_values_as_needed()
            self.update_group_field_if_needed()
            self.update_id_field_if_needed()
            self.save_json_to_destination_file()
            return SUCCESS_RETURN_CODE
        except Exception as err:
            if self.verbose:
                click.secho(f'\nFailed to update file {self.source_file}. Error: {err}', fg='red')
            return ERROR_RETURN_CODE

    def format_file(self) -> Tuple[int, int]:
        """Manager function for the generic field JSON updater."""
        format_res = self.run_format()
        if format_res:
            return format_res, SKIP_RETURN_CODE
        else:
            return format_res, self.initiate_file_validator(GenericFieldValidator)

    def update_id_field_if_needed(self):
        """Add to 'id' field of a generic field object the default prefix '_generics' if needed"""
        generic_field_id = str(self.data.get("id"))
        if not generic_field_id.startswith(GENERIC_FIELD_DEFAULT_ID_PREFIX):
            updated_id = f'{GENERIC_FIELD_DEFAULT_ID_PREFIX}{generic_field_id}'
            if self.assume_yes:
                if self.verbose:
                    click.echo(f'Adding to id field the default prefix: {GENERIC_FIELD_DEFAULT_ID_PREFIX}')
                self.data['id'] = updated_id

            else:
                set_from_version = str(
                    input(f"\nYour current id is: '{generic_field_id}'. Do you want to set it to"
                          f" '{updated_id}'? Y/N ")).lower()
                if set_from_version in ['y', 'yes']:
                    self.data['id'] = updated_id

    def update_group_field_if_needed(self):
        """Changes 'group' field of a generic field object to default if needed"""

        group = self.data.get("group")
        if group:
            if group != GENERIC_FIELD_DEFAULT_GROUP:
                if self.verbose:
                    click.echo(f'Setting group field to default: {GENERIC_FIELD_DEFAULT_GROUP}')
                self.data['group'] = GENERIC_FIELD_DEFAULT_GROUP

        # field group is missing
        else:
            if self.verbose:
                click.echo(f'Adding a group field with a default value: {GENERIC_FIELD_DEFAULT_GROUP}')
            self.data['group'] = GENERIC_FIELD_DEFAULT_GROUP
