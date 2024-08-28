from abc import ABC
from io import StringIO
from pathlib import Path
from typing import Any, Optional, Type, Union

from demisto_sdk.commands.common.files.errors import FileLoadError, FileWriteError
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.handlers.xsoar_handler import XSOAR_Handler
from demisto_sdk.commands.common.logger import logger


class StructuredFile(TextFile, ABC):
    default_handler: Type[XSOAR_Handler]

    @property
    def handler(self) -> XSOAR_Handler:
        return getattr(self, "_handler")

    @classmethod
    def as_path(cls, path: Path, **kwargs):
        instance = super().as_path(path, **kwargs)
        instance._handler = kwargs.get("handler") or cls.default_handler
        return instance

    @classmethod
    def as_default(cls, **kwargs):
        instance = super().as_default(**kwargs)
        instance._handler = kwargs.get("handler") or cls.default_handler
        return instance

    def load(self, file_content: bytes) -> Any:
        file_content_as_text = super().load(file_content)
        try:
            return self.handler.load(StringIO(file_content_as_text))
        except Exception as error:
            raise FileLoadError(
                error, class_name=self.__class__.__name__, path=self.safe_path
            )

    @classmethod
    def write(
        cls,
        data: Any,
        output_path: Union[Path, str],
        encoding: Optional[str] = None,
        handler: Optional[XSOAR_Handler] = None,
        indent: Optional[int] = None,
        sort_keys: bool = False,
        **kwargs,
    ):
        output_path = Path(output_path)

        try:
            cls.as_default(encoding=encoding, handler=handler).write_safe_unicode(
                data, path=output_path, indent=indent, sort_keys=sort_keys, **kwargs
            )
        except Exception as e:
            logger.error(f"Could not write {output_path} as {cls.__name__} file")
            raise FileWriteError(output_path, exc=e)

    def _do_write(self, data: Any, path: Path, **kwargs) -> None:
        with path.open("w", encoding=self.encoding) as output_file:
            self.handler.dump(data, output_file, **kwargs)
