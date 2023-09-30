from typing import Any, Optional, Set

from demisto_sdk.commands.common.files.file import File


class BinaryFile(File):
    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {".png", ".bin"}

    def __read(self, file_content: bytes) -> Any:
        return file_content

    def write(self, data: Any, encoding: Optional[str] = None) -> None:
        self.output_path.write_bytes(data)
