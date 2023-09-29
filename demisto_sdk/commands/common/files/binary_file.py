from io import BytesIO
from typing import Any, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
)
from demisto_sdk.commands.common.files.file import File


class BinaryFile(File):
    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {".png", ".bin"}

    def read_local_file(self) -> bytes:
        return self.input_path.read_bytes()

    def _file_content_to_bytes(self, file_content: str) -> bytes:
        # TODO - check how to fix reading remote binary files
        try:
            return BytesIO(file_content.encode(self.default_encoding)).read()
        except UnicodeEncodeError:
            return BytesIO(
                file_content.encode(self.input_path_original_encoding)
            ).read()

    def read_git_file(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH, from_remote: bool = True
    ):
        return self._file_content_to_bytes(
            super().read_git_file(tag, from_remote=from_remote)
        )

    def write(self, data: Any, encoding: Optional[str] = None) -> None:
        self.output_path.write_bytes(data)
