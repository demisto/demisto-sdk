import base64
from pathlib import Path

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.prepare_content.unifier import Unifier


class XDRCTemplateUnifier(Unifier):
    @staticmethod
    def unify(
        path: Path, data: dict, marketplace: MarketplaceVersions = None, **kwargs
    ) -> dict:
        logger.info(f"Unifying {path}...")
        data = XDRCTemplateUnifier._insert_yaml_template(path, data)
        logger.info(f"<green>Successfully created a unified JSON in {path}</green>")
        return data

    @staticmethod
    def _insert_yaml_template(path: Path, output_data: dict):
        yaml_template_path = path.with_suffix(".yml")
        encoding = "utf-8"
        with open(yaml_template_path) as yaml_template_file:
            output_data["yaml_template"] = base64.b64encode(
                yaml_template_file.read().encode(encoding)
            ).decode(encoding)
        return output_data
