import re
from typing import Any, List, Set

from demisto_sdk.commands.common.files.file import File


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

    def search_text(self, regex_pattern: str) -> List[str]:
        return re.findall(regex_pattern, string=self.read_local_file())

    def write(self, data: Any) -> None:
        self.output_path.write_text(data=data, encoding=self.default_encoding)
