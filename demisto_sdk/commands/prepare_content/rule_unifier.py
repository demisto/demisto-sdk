import os
from collections import defaultdict
from pathlib import Path

from ruamel.yaml.scalarstring import (  # noqa: TID251 - only importing FoldedScalarString is OK
    FoldedScalarString,
)

from demisto_sdk.commands.common.constants import SAMPLES_DIR, MarketplaceVersions
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.prepare_content.unifier import Unifier

json = JSON_Handler()


class RuleUnifier(Unifier):
    @staticmethod
    def unify(
        path: Path, data: dict, marketplace: MarketplaceVersions = None, **kwargs
    ) -> dict:
        logger.info(f"Unifiying {path}...")
        RuleUnifier._insert_rules(path, data)
        RuleUnifier._insert_schema(path, data)
        RuleUnifier._insert_samples(path, data)
        logger.info(f"<green>Successfully created unified YAML in {path}</green>")
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
                sample = get_file(Path(samples_dir) / sample_file, raise_on_error=True)
                if data.get("id") in sample.get("rules", []):
                    samples[f'{sample.get("vendor")}_{sample.get("product")}'].extend(
                        sample.get("samples")
                    )
            if samples:
                data["samples"] = FoldedScalarString(json.dumps(samples, indent=4))
                logger.info(f"Added {len(samples)} samples.")
            else:
                logger.info("Did not find matching samples.")

    @staticmethod
    def _insert_schema(path: Path, data: dict):
        schema_path = str(path).replace(".yml", "_schema.json")
        if Path(schema_path).exists():
            with open(schema_path, encoding="utf-8") as schema_file:
                schema = json.loads(schema_file.read())
                data["schema"] = FoldedScalarString(json.dumps(schema, indent=4))
        else:
            logger.info("No schema file was found.")
