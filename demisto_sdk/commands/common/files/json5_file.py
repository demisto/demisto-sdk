from pydantic import Field, validator

from demisto_sdk.commands.common.files.json_yml_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from demisto_sdk.commands.common.handlers import JSON5_Handler


class Json5File(StructuredFile):
    handler: JSON5_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: JSON5_Handler) -> JSON5_Handler:
        return v or json5
