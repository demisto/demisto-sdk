import re
from pathlib import Path
from typing import Any, List

from bs4.dammit import UnicodeDammit

from demisto_sdk.commands.common.constants import PACKS_WHITELIST_FILE_NAME
from demisto_sdk.commands.common.files.errors import (
    LocalFileReadError,
)
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.logger import logger


class TextFile(File):
    @classmethod
    def with_local_path(cls, path: Path, **kwargs):
        instance = super().with_local_path(path)
        instance._encoding = kwargs.get("encoding") or "utf-8"
        return instance

    @classmethod
    def as_default(cls, **kwargs):
        instance = super().as_default()
        instance._encoding = kwargs.get("encoding") or "utf-8"
        return instance

    @property
    def encoding(self) -> str:
        return getattr(self, "_encoding", "")

    @property
    def num_lines(self):
        return len(self.__read_local_file().splitlines())

    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.name.lower() in {
            "command-examples",
            "command_example",
            "command_examples",
            PACKS_WHITELIST_FILE_NAME,
        } or path.suffix.lower() in {".md", ".py", ".txt"}

    def load(self, file_content: bytes) -> Any:
        try:
            return file_content.decode(self.encoding)
        except UnicodeDecodeError:
            original_file_encoding = UnicodeDammit(file_content).original_encoding
            logger.debug(
                f"Error when decoding file {self.path} with {self.encoding}, "
                f"trying to decode the file with original encoding {original_file_encoding}"
            )
            try:
                return UnicodeDammit(file_content).unicode_markup
            except UnicodeDecodeError as e:
                logger.error(f"Could not auto detect encoding for file {self.path}")
                raise LocalFileReadError(self.path, exc=e)
        except Exception as e:
            raise LocalFileReadError(self.path, exc=e)

    def search_text(self, regex_pattern: str) -> List[str]:
        return re.findall(regex_pattern, string=self.__read_local_file())

    def __write(self, data: Any, path: Path, **kwargs) -> None:

        if self.encoding != "utf-8":
            self._do_write(data, path=path, **kwargs)
        else:
            try:
                self._do_write(data, path=path, **kwargs)
            except UnicodeDecodeError:
                original_file_encoding = UnicodeDammit(
                    path.read_bytes()
                ).original_encoding
                if original_file_encoding == "utf-8":
                    logger.error(
                        f"{path} is encoded as unicode, cannot handle the error, raising it"
                    )
                    raise

                logger.debug(
                    f"deleting {path} - it will be rewritten as unicode (was {original_file_encoding})"
                )
                path.unlink()  # deletes the file
                logger.debug(f"rewriting {path} as unicode file")
                self._do_write(data, path=path, **kwargs)  # recreates the file

    def _do_write(self, data: Any, path: Path, **kwargs) -> None:
        path.write_text(data=data, encoding=self.encoding)
