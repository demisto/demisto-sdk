from abc import ABC
from io import StringIO
from pathlib import Path
from typing import Any, Optional, Type

from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler


class StructuredFile(TextFile, ABC):

    default_handler: Type[XSOAR_Handler]

    @property
    def handler(self) -> XSOAR_Handler:
        return getattr(self, "_handler")

    @classmethod
    def with_local_path(cls, path: Path, **kwargs):
        instance = super().with_local_path(path, **kwargs)
        instance._handler = kwargs.get("handler") or cls.default_handler
        return instance

    @classmethod
    def as_default(cls, **kwargs):
        instance = super().as_default(**kwargs)
        instance._handler = kwargs.get("handler") or cls.default_handler
        return instance

    def load(self, file_content: bytes) -> Any:
        return self.handler.load(StringIO(super().load(file_content)))

    @classmethod
    def do_custom_write(
        cls,
        data: Any,
        output_path: Path,
        handler: Optional[XSOAR_Handler] = None,
        encoding: Optional[str] = None,
        indent: int=None,
        sort_keys=False,
        **kwargs
    ):
        cls.write_file(
            data,
            output_path,
            encoding=encoding,
            handler=handler,
            indent=indent,
            sort_keys=sort_keys,
            **kwargs
        )

    def _do_write(self, data: Any, path: Path, **kwargs) -> None:
        with path.open("w", encoding=self.encoding) as output_file:
            self.handler.dump(data, output_file, **kwargs)
