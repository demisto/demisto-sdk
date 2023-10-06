from abc import ABC, abstractmethod
from functools import lru_cache
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import Field, validator

from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class HandlerFile(TextFile, ABC):

    handler: XSOAR_Handler = Field(None, exclude=True)

    @validator("handler", always=True)
    @abstractmethod
    def validate_handler(cls, v: Type[XSOAR_Handler]) -> Type[XSOAR_Handler]:
        raise NotImplementedError("validate_handler must be implemented")

    @classmethod
    @lru_cache
    def read_from_file_content(
        cls,
        file_content: Union[bytes, BytesIO],
        handler: Optional[XSOAR_Handler] = None,
    ):
        return super().read_from_file_content(
            file_content, handler=cls.validate_handler()
        )

    def load(self, file_content: bytes) -> Union[List, Dict]:
        return self.handler.load(StringIO(super().load(file_content)))

    @classmethod
    def write_file(
        cls,
        data: Any,
        output_path: Union[Path, str],
        encoding: Optional[str] = None,
        handler: Optional[XSOAR_Handler] = None,
    ):
        return super().write_file(
            data,
            output_path=output_path,
            encoding=encoding,
            handler=cls.validate_handler(handler),
        )

    def _write(self, data: Any, path: Path, encoding: Optional[str] = None) -> None:
        with path.open("w", encoding=encoding or self.default_encoding) as output_file:
            self.handler.dump(data, output_file)
