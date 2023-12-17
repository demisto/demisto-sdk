from pathlib import Path

from pydantic import Field, validator

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.handlers import YAML_Handler


class YmlFile(StructuredFile):
    handler: YAML_Handler = Field(None, exclude=True)

    # TODO[pydantic]: We couldn't refactor the `validator`, please replace it by `field_validator` manually.
    # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-validators for more information.
    @validator("handler", always=True)
    def validate_handler(cls, v: YAML_Handler) -> YAML_Handler:
        return v or yaml

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() in {
            ".yml",
            ".yaml",
        }
