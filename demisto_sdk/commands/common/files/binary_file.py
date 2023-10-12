from pathlib import Path
from typing import Any, Optional

from demisto_sdk.commands.common.files.file import File


class BinaryFile(File):
    def load(self, file_content: bytes) -> bytes:
        return file_content

    def _write(self, data: Any, path: Path, encoding: Optional[str] = None):
        path.write_bytes(data)
