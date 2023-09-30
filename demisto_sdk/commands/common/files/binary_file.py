from typing import Any, Optional, Set

from demisto_sdk.commands.common.constants import (
    DEMISTO_GIT_PRIMARY_BRANCH,
)
from demisto_sdk.commands.common.files.errors import FileReadError
from demisto_sdk.commands.common.files.file import File


class BinaryFile(File):
    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {".png", ".bin"}

    def read_local_file(self) -> bytes:
        return self.input_path.read_bytes()

    def read_git_file(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH, from_remote: bool = True
    ):
        try:
            return self.git_util.read_file_content(
                self.input_path, commit_or_branch=tag, from_remote=from_remote
            )
        except Exception as e:
            raise FileReadError(self.input_path, exc=e)

    def write(self, data: Any, encoding: Optional[str] = None) -> None:
        self.output_path.write_bytes(data)
