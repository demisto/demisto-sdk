from io import BytesIO
from typing import Any, Set

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

    def read_local_file_git(self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH) -> bytes:
        return self._file_content_to_bytes(super().read_local_file_git(tag))

    def read_origin_file_git(self, branch: str = DEMISTO_GIT_PRIMARY_BRANCH) -> bytes:
        return self._file_content_to_bytes(super().read_origin_file_git(branch))

    def write(self, data: Any) -> None:
        self.output_path.write_bytes(data)
