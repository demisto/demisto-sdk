from typing import Any, Set, List
import zipfile
from demisto_sdk.commands.common.files.compressed_file import CompressedFile
from demisto_sdk.commands.common.files.file import File
from pydantic import validator
import tarfile


class TarFile(CompressedFile):

    tar_file: tarfile.TarFile

    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {'.tar'}

    @validator("tar_file")
    def validate_tar_file(self, values):
        return tarfile.open(values["input_path"], mode='a')

    @property
    def files_names(self) -> List[str]:
        return self.tar_file.getnames()

    def read_local_file(self) -> Any:
        self.tar_file.extractall(self.input_path)
        return self

    def read_single_file(self, file_name: str):
        if not (self.input_path / file_name).exists():
            self.tar_file.extractall(self.input_path)
        with self.tar_file.extractfile(file_name) as file:
            return File.read_from_local_path(file.name, git_util=self.git_util)
