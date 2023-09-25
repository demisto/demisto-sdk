from abc import ABC, abstractmethod
from pathlib import Path
from typing import Type

import pytest

from demisto_sdk.commands.common.files.binary_file import BinaryFile
from demisto_sdk.commands.common.files.errors import UnknownFileException
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.files.ini_file import IniFile
from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.files.yml_file import YmlFile
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.legacy_git_tools import git_path

DEMISTO_SDK_PATH = Path(f"{git_path()}", "demisto_sdk")


class TestFileFromPath:
    @pytest.mark.parametrize(
        "input_path, expected_class",
        [
            (DEMISTO_SDK_PATH / "tests/test_files/just_a_txt_file.txt", TextFile),
            (DEMISTO_SDK_PATH / "tests/test_files/layout-valid.json", JsonFile),
            (DEMISTO_SDK_PATH / "tests/test_files/script-test_script.yml", YmlFile),
            (DEMISTO_SDK_PATH / "pytest.ini", IniFile),
            (
                DEMISTO_SDK_PATH / "tests/test_files/fake_pack/Author_image.png",
                BinaryFile,
            ),
        ],
    )
    def test_from_path_input_file(self, input_path: Path, expected_class: Type[File]):
        assert isinstance(File.from_path(input_path), expected_class)

    def test_from_path_input_file_unknown_file(self):
        with pytest.raises(UnknownFileException):
            File.from_path("path_does_not_exist")

    def test_from_path_input_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            File.from_path("path_does_not_exist.yml")

    @pytest.mark.parametrize(
        "output_path, expected_class",
        [
            (DEMISTO_SDK_PATH / "test.txt", TextFile),
            (DEMISTO_SDK_PATH / "test.json", JsonFile),
            (DEMISTO_SDK_PATH / "test.yml", YmlFile),
            (DEMISTO_SDK_PATH / "test.ini", IniFile),
            (DEMISTO_SDK_PATH / "test.png", BinaryFile),
            (DEMISTO_SDK_PATH / ".pack-ignore", IniFile),
            (DEMISTO_SDK_PATH / ".secrets-ignore", TextFile),
            (DEMISTO_SDK_PATH / "command_examples", TextFile),
        ],
    )
    def test_from_path_output_file(self, output_path: Path, expected_class: Type[File]):
        assert isinstance(File.from_path(output_path=output_path), expected_class)

    def test_from_path_output_file_no_suffix(self):
        with pytest.raises(ValueError):
            File.from_path(output_path="bla")


class FileReadMethodsTesting(ABC):
    @pytest.fixture(autouse=True)
    @abstractmethod
    def input_files(self):
        pass

    @staticmethod
    def get_local_remote_file_path_side_effect(full_file_path: str, tag: str):
        git_util = GitUtil.from_content_path()
        return f"{tag}:{git_util.path_from_git_root(full_file_path)}"

    @abstractmethod
    def test_read_from_local_path(self, input_files):
        pass

    @abstractmethod
    def test_read_from_origin_git_path(self, mocker, input_files):
        pass

    @abstractmethod
    def test_read_from_local_git_path(self, input_files):
        pass
