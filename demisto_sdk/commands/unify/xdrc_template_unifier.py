import base64
import json
import os
from pathlib import Path

import click

from demisto_sdk.commands.common.constants import DIR_TO_PREFIX
from demisto_sdk.commands.common.errors import Errors
from demisto_sdk.commands.common.tools import get_yml_paths_in_dir


class XDRCTemplateUnifier:
    def __init__(
        self,
        input: str,
        output: Path = None,
        dir_name: str = 'XDRCTemplates',
    ):
        self.input_xdrc_template = input

        if dir_name:
            self.dir_name = dir_name

        input = os.path.abspath(input)
        self.package_path = input.rstrip(os.sep)

        _, self.yml_path = get_yml_paths_in_dir(self.package_path, Errors.no_yml_file(self.package_path))

        self.dest_path = os.path.abspath(output) if output else None

    def unify(self):
        click.echo(f'Unifying {self.package_path}...')
        self._set_dest_path()
        output_data = self._insert_xdrc_template()
        self._insert_yaml_template(output_data)
        self._output_json(file_data=output_data)
        click.secho(f'Successfully created unified JSON in {self.dest_path}', fg="green")

        return [str(self.dest_path)]

    def _set_dest_path(self, file_name_suffix: str = None,):
        """Sets the target (destination) output path for the unified JSON"""
        package_dir_name = os.path.basename(self.package_path)
        output_filename = '{}-{}-{}.json'.format('external', DIR_TO_PREFIX[self.dir_name], package_dir_name)

        if file_name_suffix:
            # append suffix to output file name
            output_filename = file_name_suffix.join(os.path.splitext(output_filename))

        if self.dest_path:
            self.dest_path = os.path.join(self.dest_path, output_filename)
        else:
            self.dest_path = os.path.join(self.package_path, output_filename)

    def _insert_xdrc_template(self):
        xdrc_template_path = Path(self.yml_path).with_suffix('.json')

        with open(xdrc_template_path) as xdrc_template_file:
            xdrc_template = json.load(xdrc_template_file)

        return xdrc_template

    def _insert_yaml_template(self, output_data):
        yaml_template_path = Path(self.yml_path)
        encoding = 'utf-8'
        with open(yaml_template_path, "r") as yaml_template_file:
            output_data['yaml_template'] = base64.b64encode(yaml_template_file.read().encode(encoding)).decode(encoding)

    def _output_json(self, file_data):
        with open(self.dest_path, mode='w+') as dest_file:  # type: ignore
            json.dump(file_data, dest_file)
