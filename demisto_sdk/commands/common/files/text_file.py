import re
from typing import Any, List, Optional, Set

from bs4 import UnicodeDammit

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.logger import logger


class TextFile(File):
    @property
    def num_lines(self):
        return len(self.read_local_file().splitlines())

    @classmethod
    def known_files(cls):
        return {".secrets-ignore", "command_examples"}

    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {
            ".txt",
            ".text",
            ".py",
            ".md",
            ".xif",
        }

    def load(self, file_content: str) -> Any:
        return file_content

    def safe_load(self, file_content: str) -> Any:
        try:
            return self.load(file_content)
        except Exception as e:
            logger.error(f"Error when loading file {self.input_path}\nerror:{e}")
            raise FileReadError(self.input_path, exc=e)

    def load_text(self, file_content: bytes) -> str:
        try:
            return file_content.decode(self.default_encoding)
        except UnicodeDecodeError:
            try:
                return UnicodeDammit(file_content).unicode_markup
            except UnicodeDecodeError as e:
                logger.error(
                    f"Could not auto detect encoding for file {self.input_path}"
                )
                raise FileReadError(self.input_path, exc=e)

    def read_local_file(self) -> Any:
        file_content = self.load_text(super().read_local_file())
        return self.safe_load(file_content)

    def read_git_file(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH, from_remote: bool = True
    ):
        file_content = self.load_text(
            super().read_git_file(tag, from_remote=from_remote)
        )
        return self.safe_load(file_content)

    def search_text(self, regex_pattern: str) -> List[str]:
        return re.findall(regex_pattern, string=self.read_local_file())

    def write(self, data: Any, encoding: Optional[str] = None) -> None:
        self.output_path.write_text(
            data=data, encoding=encoding or self.default_encoding
        )
