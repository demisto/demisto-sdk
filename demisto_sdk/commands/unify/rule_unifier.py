import io
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Optional

import click
from ruamel.yaml.scalarstring import FoldedScalarString

from demisto_sdk.commands.common.constants import SAMPLES_DIR
from demisto_sdk.commands.unify.yaml_unifier import YAMLUnifier


class RuleUnifier(YAMLUnifier):
    def __init__(
        self,
        input: str,
        output: Optional[str] = None,
        force: bool = False,
        marketplace: Optional[str] = None,
    ):
        self.input_rule = input

        super().__init__(
            input=input,
            output=output,
            force=force,
            marketplace=marketplace
        )

        self.dir_name = os.path.basename(os.path.dirname(self.package_path))

    def unify(self):
        click.echo(f'Unifiying {self.package_path}...')
        self._set_dest_path()
        self._insert_rules()
        self._insert_schema()
        self._insert_samples()
        self._output_yaml(file_path=self.dest_path, file_data=self.yml_data)
        click.secho(f'Successfully created unifyed YAML in {self.dest_path}', fg="green")

        return [str(self.dest_path)]

    def _insert_rules(self):
        rules_path = Path(self.yml_path).with_suffix('.xif')
        with io.open(rules_path, mode='r', encoding='utf-8') as rules_file:
            rules = rules_file.read()
            self.yml_data['rules'] = FoldedScalarString(rules)

    def _insert_samples(self):
        samples_dir = os.path.join(os.path.dirname(self.package_path), SAMPLES_DIR)
        if os.path.isdir(samples_dir):
            samples = defaultdict(list)
            for sample_file in os.listdir(samples_dir):
                with io.open(os.path.join(samples_dir, sample_file), mode='r', encoding='utf-8') as samples_file_object:
                    sample = json.loads(samples_file_object.read())
                    if self.yml_data.get('id') in sample.get('rules', []):
                        samples[f'{sample.get("vendor")}_{sample.get("product")}'].extend(sample.get('samples'))
            if samples:
                self.yml_data['samples'] = FoldedScalarString(json.dumps(samples, indent=4))
                click.echo(f'Added {len(samples)} samples.')
            else:
                click.echo('Did not find matching samples.')

    def _insert_schema(self):
        schema_path = self.yml_path.replace('.yml', '_schema.json')
        if os.path.exists(schema_path):
            with io.open(schema_path, mode='r', encoding='utf-8') as schema_file:
                schema = json.loads(schema_file.read())
                self.yml_data['schema'] = FoldedScalarString(json.dumps(schema, indent=4))
        else:
            click.echo('No schema file was found.')
