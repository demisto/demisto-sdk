import base64
import copy
import io
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

import click
from ruamel.yaml.scalarstring import FoldedScalarString

from demisto_sdk.commands.common.constants import SAMPLES_DIR, DIR_TO_PREFIX
from demisto_sdk.commands.unify.yaml_unifier import YAMLUnifier


class AgentConfigUnifier(YAMLUnifier):
    def __init__(
        self,
        input: str,
        output: Optional[str] = None,
        force: bool = False,
        dir_name: Optional[str] = 'AgentConfigs',
        marketplace: Optional[str] = None,
    ):
        self.input_agent_config = input

        super().__init__(
            input=input,
            output=output,
            force=force,
            marketplace=marketplace
        )
        if dir_name:
            self.dir_name = dir_name

    def unify(self):
        click.echo(f'Unifiying {self.package_path}...')
        self._set_dest_path()
        output_data = {}
        output_data = self._insert_agent_config()
        self._insert_yaml_template(output_data)
        self._output_json(file_data=output_data)
        click.secho(f'Successfully created unifyed JSON in {self.dest_path}', fg="green")

        return [str(self.dest_path)]

    def _set_dest_path(self, file_name_suffix: Optional[str] = None,):
        """Sets the target (destination) output path for the unified JSON"""
        package_dir_name = os.path.basename(self.package_path)
        output_filename = '{}-{}.json'.format(DIR_TO_PREFIX[self.dir_name], package_dir_name)

        if file_name_suffix:
            # append suffix to output file name
            output_filename = file_name_suffix.join(os.path.splitext(output_filename))

        if self.dest_path:
            self.dest_path = os.path.join(self.dest_path, output_filename)
        else:
            self.dest_path = os.path.join(self.package_path, output_filename)

    def _insert_agent_config(self):
        agent_config_path = Path(self.yml_path).with_suffix('.json')

        with open(agent_config_path) as agent_config_file:
            agent_config = json.load(agent_config_file)

        return agent_config

    def _insert_yaml_template(self, output_data):
        yaml_template_path = Path(self.yml_path)
        encoding = 'utf-8'
        with open(yaml_template_path, "r") as yaml_template_file:
            output_data['yaml_template'] = base64.b64encode(yaml_template_file.read().encode(encoding)).decode(encoding)

    def _output_json(self, file_data):
        with open(self.dest_path, mode='w') as dest_file:  # type: ignore
            json.dump(file_data, dest_file)

