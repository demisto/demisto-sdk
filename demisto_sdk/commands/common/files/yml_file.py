from typing import Set

from pydantic import Field, validator

from demisto_sdk.commands.common.files.handler_file import HandlerFile
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.handlers import YAML_Handler


class YmlFile(HandlerFile):
    handler: YAML_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: YAML_Handler) -> YAML_Handler:
        return v or yaml

    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {".yaml", ".yml"}
