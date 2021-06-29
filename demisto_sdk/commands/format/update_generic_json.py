from distutils.version import LooseVersion

import click
import ujson
import yaml
from demisto_sdk.commands.common.tools import print_error
from demisto_sdk.commands.format.format_constants import (
    ARGUMENTS_DEFAULT_VALUES, TO_VERSION_5_9_9)
from demisto_sdk.commands.format.update_generic import BaseUpdate


class BaseUpdateJSON(BaseUpdate):
    """BaseUpdateJSON is the base class for all json updaters.
        Attributes:
            input (str): the path to the file we are updating at the moment.
            output (str): the desired file name to save the updated version of the YML to.
            data (Dict): JSON file data arranged in a Dict.
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

    def set_default_values_as_needed(self):
        """Sets basic arguments of reputation commands to be default, isArray and required."""
        if self.verbose:
            click.echo('Updating required default values')
        for field in ARGUMENTS_DEFAULT_VALUES:
            if self.__class__.__name__ in ARGUMENTS_DEFAULT_VALUES[field][1]:
                self.data[field] = ARGUMENTS_DEFAULT_VALUES[field][0]

    def save_json_to_destination_file(self):
        """Save formatted JSON data to destination file."""
        if self.source_file != self.output_file:
            click.secho(f'Saving output JSON file to {self.output_file}', fg='white')
        with open(self.output_file, 'w') as file:
            ujson.dump(self.data, file, indent=4, encode_html_chars=True, escape_forward_slashes=False,
                       ensure_ascii=False)

    def update_json(self):
        """Manager function for the generic JSON updates."""
        self.set_version_to_default()
        self.remove_null_fields()
        self.remove_unnecessary_keys()
        self.set_fromVersion(from_version=self.from_version)

    def set_toVersion(self):
        """
        Sets toVersion key in file
        Relevant for old entities such as layouts and classifiers.
        """
        if not self.data.get('toVersion') or LooseVersion(self.data.get('toVersion', '99.99.99')) >= TO_VERSION_5_9_9:
            if self.verbose:
                click.echo('Setting toVersion field')
            self.data['toVersion'] = TO_VERSION_5_9_9

    def set_description(self):
        """Add an empty description to file root."""
        if 'description' not in self.data:
            if self.verbose:
                click.echo('Adding empty descriptions to root')
            self.data['description'] = ''

    def remove_null_fields(self):
        """Remove empty fields from file root."""
        with open(self.schema_path, 'r') as file_obj:
            schema_data = yaml.safe_load(file_obj)
        schema_fields = schema_data.get('mapping').keys()
        for field in schema_fields:
            # We want to keep 'false' and 0 values, and avoid removing fields that are required in the schema.
            if field in self.data and self.data[field] in (None, '', [], {}) and \
                    not schema_data.get('mapping', {}).get(field, {}).get('required'):
                self.data.pop(field)

    def update_id(self, field='name'):
        """Updates the id to be the same as the provided field ."""

        if self.verbose:
            click.echo('Updating ID')
        if field not in self.data:
            print_error(f'Missing {field} field in file {self.source_file} - add this field manually')
            return
        self.data['id'] = self.data[field]
