import json
import os
from collections import defaultdict
from pathlib import Path

import click
from ruamel.yaml.scalarstring import FoldedScalarString

from demisto_sdk.commands.common.constants import SAMPLES_DIR, MarketplaceVersions
from demisto_sdk.commands.prepare_content.unifier import Unifier


class RuleUnifier(Unifier):
    @staticmethod
    def unify(
        path: Path, data: dict, marketplace: MarketplaceVersions = None, **kwargs
    ) -> dict:
        click.echo(f"Unifiying {path}...")
        RuleUnifier._insert_rules(path, data)
        RuleUnifier._insert_schema(path, data)
        RuleUnifier._insert_samples(path, data)
        click.secho(f"Successfully created unified YAML in {path}", fg="green")
        return data

    @staticmethod
    def _insert_rules(path: Path, data: dict):
        rules_path = path.with_suffix(".xif")
        with open(rules_path, encoding="utf-8") as rules_file:
            rules = rules_file.read()
            data["rules"] = FoldedScalarString(rules)

    @staticmethod
    def _insert_samples(path: Path, data: dict):
        samples_dir = os.path.join(os.path.dirname(path), SAMPLES_DIR)
        if os.path.isdir(samples_dir):
            samples = defaultdict(list)
            for sample_file in os.listdir(samples_dir):
                with open(
                    os.path.join(samples_dir, sample_file), encoding="utf-8"
                ) as samples_file_object:
                    sample = json.loads(samples_file_object.read())
                    if data.get("id") in sample.get("rules", []):
                        samples[
                            f'{sample.get("vendor")}_{sample.get("product")}'
                        ].extend(sample.get("samples"))
            if samples:
                data["samples"] = FoldedScalarString(json.dumps(samples, indent=4))
                click.echo(f"Added {len(samples)} samples.")
            else:
                click.echo("Did not find matching samples.")

    @staticmethod
    def _insert_schema(path: Path, data: dict):
        schema_path = str(path).replace(".yml", "_schema.json")
        if os.path.exists(schema_path):
            with open(schema_path, encoding="utf-8") as schema_file:
                schema = json.loads(schema_file.read())
                data["schema"] = FoldedScalarString(json.dumps(schema, indent=4))
        else:
            click.echo("No schema file was found.")
