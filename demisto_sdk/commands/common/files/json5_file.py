from pathlib import Path

from pydantic import Field, validator

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from demisto_sdk.commands.common.handlers import JSON5_Handler


class Json5File(StructuredFile):

    handler: JSON5_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: JSON5_Handler) -> JSON5_Handler:
        return v or json5

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() == ".json5"
