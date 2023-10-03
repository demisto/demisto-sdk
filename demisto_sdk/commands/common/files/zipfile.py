from typing import Any, Set, List
import zipfile

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.compressed_file import CompressedFile
from demisto_sdk.commands.common.files.file import File
from pydantic import validator


class ZipFile(CompressedFile):

    zip_file: zipfile.ZipFile

    @classmethod
    def known_extensions(cls) -> Set[str]:
        return {'.zip'}

    @validator("zip_file")
    def validate_zip_file(self, values):
        return zipfile.ZipFile(values["input_path"], mode='a')

    def files_names(self) -> List[str]:
        return self.zip_file.namelist()

    def read_local_file(self) -> Any:
        self.zip_file.extractall(self.input_path)
        return self

    def read_git_file(
        self, tag: str = DEMISTO_GIT_PRIMARY_BRANCH, from_remote: bool = True
    ):
        pass

    def read_single_file(self, file_name: str):
        if not (self.input_path / file_name).exists():
            self.zip_file.extractall(self.input_path)

        self.zip_file.extract(file_name)
        with self.zip_file.open(str(self.input_path / file_name)) as file:
            return File.read_from_local_path(file.name, git_util=self.git_util)
