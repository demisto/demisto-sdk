from pathlib import Path
from typing import Any, Optional

from demisto_sdk.commands.common.files.file import File


class BinaryFile(File):
    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() in {".png", ".svg", ".bin"}

    def load(self, file_content: bytes) -> bytes:
        return file_content

    def _write(self, data: Any, path: Path, encoding: Optional[str] = None, **kwargs):
        path.write_bytes(data)
