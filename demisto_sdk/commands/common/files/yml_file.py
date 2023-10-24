from pydantic import Field, validator

from demisto_sdk.commands.common.files.json_yml_file import JsonYmlFile
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.handlers import YAML_Handler


class YmlFile(JsonYmlFile):
    handler: YAML_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: YAML_Handler) -> YAML_Handler:
        return v or yaml
