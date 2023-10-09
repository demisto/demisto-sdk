from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Type

import pytest

from demisto_sdk.commands.common.files.binary_file import BinaryFile
from demisto_sdk.commands.common.files.errors import HttpFileReadError, UnknownFileError
from demisto_sdk.commands.common.files.file import File
from demisto_sdk.commands.common.files.ini_file import IniFile
from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.files.yml_file import YmlFile
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.legacy_git_tools import git_path
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD

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

    def test_from_path_with_input_path_from_content(self, git_repo: Repo):
        integration = git_repo.create_pack("test").create_integration("test")
        with ChangeCWD(git_repo.path):
            if git_util := git_repo.git_util:
                assert isinstance(
                    File.from_path(git_util.path_from_git_root(integration.yml.path)),
                    YmlFile,
                )

    def test_from_path_input_file_unknown_file(self):
        with pytest.raises(UnknownFileError):
            File.from_path("path_does_not_exist")

    def test_from_path_input_file_does_not_exist(self):
        with pytest.raises(FileNotFoundError):
            File.from_path("path_does_not_exist.yml")

    def test_read_from_file_content_error(self):
        with pytest.raises(ValueError):
            File.read_from_file_content(b"")

    def test_read_from_http_request_invalid_url(self):
        with pytest.raises(HttpFileReadError):
            File.read_from_http_request("not/valid/url")

    def test_write_file_error(self):
        with pytest.raises(ValueError):
            File.write_file({}, output_path="some/path")


class FileObjectsTesting(ABC):
    @pytest.fixture(autouse=True)
    @abstractmethod
    def input_files(self):
        pass

    @staticmethod
    def get_local_remote_file_path_side_effect(
        full_file_path: str, tag: str, from_remote: bool
    ):
        git_util = GitUtil.from_content_path()
        return f"{tag}:{git_util.path_from_git_root(full_file_path)}"

    @abstractmethod
    def test_read_from_local_path(self, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_read_from_github_api(self, mocker, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_read_from_gitlab_api(self):
        pass

    @abstractmethod
    def test_read_from_http_request(self):
        pass

    @abstractmethod
    def test_write_file(self):
        pass
