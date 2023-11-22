from pydantic import Field, validator

from demisto_sdk.commands.common.files.json_yml_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.handlers import YAML_Handler


class YmlFile(StructuredFile):
    handler: YAML_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: YAML_Handler) -> YAML_Handler:
        return v or yaml
