from pathlib import Path

from pydantic import Field, validator

from demisto_sdk.commands.common.files.structured_file import StructuredFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import JSON_Handler


class JsonFile(StructuredFile):
    handler: JSON_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: JSON_Handler) -> JSON_Handler:
        return v or json

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() == ".json"
