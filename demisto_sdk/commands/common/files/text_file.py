import re
from pathlib import Path
from typing import Any, List, Optional

from bs4.dammit import UnicodeDammit

from demisto_sdk.commands.common.constants import PACKS_WHITELIST_FILE_NAME
from demisto_sdk.commands.common.files.errors import LocalFileReadError
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.logger import logger


class TextFile(File):
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
            return file_content.decode(self.default_encoding)
        except UnicodeDecodeError:
            original_file_encoding = UnicodeDammit(file_content).original_encoding
            logger.debug(
                f"Error when decoding file {self.input_path} with {self.default_encoding}, "
                f"trying to decode the file with original encoding {original_file_encoding}"
            )
            try:
                return UnicodeDammit(file_content).unicode_markup
            except UnicodeDecodeError as e:
                logger.error(
                    f"Could not auto detect encoding for file {self.input_path}"
                )
                raise LocalFileReadError(self.input_path, exc=e)
        except Exception as e:
            raise LocalFileReadError(self.input_path, exc=e)

    def search_text(self, regex_pattern: str) -> List[str]:
        return re.findall(regex_pattern, string=self.__read_local_file())

    def _write(
        self, data: Any, path: Path, encoding: Optional[str] = None, **kwargs
    ) -> None:
        path.write_text(data=data, encoding=encoding or self.default_encoding)
