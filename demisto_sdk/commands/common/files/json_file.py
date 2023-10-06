from functools import lru_cache
from typing import Optional, Set

from pydantic import Field, validator

from demisto_sdk.commands.common.files.handler_file import HandlerFile
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import JSON_Handler, XSOAR_Handler


class JsonFile(HandlerFile):
    handler: JSON_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    def validate_handler(cls, v: JSON_Handler) -> JSON_Handler:
        return v or json

    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {".json"}

    @classmethod
    @lru_cache
    def read_from_file_content(
        cls,
        file_content: bytes,
        handler: Optional[XSOAR_Handler] = None,
    ):
        return super().read_from_file_content(file_content, handler=handler or json)
