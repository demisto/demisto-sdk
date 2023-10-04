import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from demisto_sdk.commands.common.files.file import File


class CompressedFile(File, ABC):
    @property
    @abstractmethod
    def files_names(self) -> List[str]:
        pass

    @property
    def num_of_files(self) -> int:
        return len(self.files_names)

    def _write(self, data: Any, path: Path, encoding: Optional[str] = None) -> None:
        shutil.make_archive(path, self.normalized_suffix, path)

    @abstractmethod
    def read_single_file(self, file_name: str):
        pass
