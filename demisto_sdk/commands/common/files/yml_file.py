from pathlib import Path

from pydantic import Field, validator

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml, XSOAR_Handler
from demisto_sdk.commands.common.handlers import YAML_Handler


class YmlFile(StructuredFile):
    default_handler: YAML_Handler = yaml

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() in {
            ".yml",
            ".yaml",
        }
