import re
from typing import Any, List, Optional, Set

from demisto_sdk.commands.common.files.file import File


class TextFile(File):
    @property
    def num_lines(self):
        return len(super().read_local_file().splitlines())

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
        return re.findall(regex_pattern, string=super().read_local_file())

    def write(self, data: Any, encoding: Optional[str] = None) -> None:
        self.output_path.write_text(
            data=data, encoding=encoding or self.default_encoding
        )
