from pathlib import Path
from typing import Any, Union

from demisto_sdk.commands.common.files.errors import FileWriteError
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.logger import logger


class BinaryFile(File):
    @classmethod
    def is_model_type_by_path(cls, path: Path) -> bool:
        return path.suffix.lower() in {".png", ".svg", ".bin"}

    def load(self, file_content: bytes) -> bytes:
        return file_content

    @classmethod
    def write(
        cls,
        data: Any,
        output_path: Union[Path, str],
    ):
        output_path = Path(output_path)

        try:
            output_path.write_bytes(data)
        except Exception as e:
            logger.error(f"Could not write {output_path} as {cls.__name__} file")
            raise FileWriteError(output_path, exc=e)
