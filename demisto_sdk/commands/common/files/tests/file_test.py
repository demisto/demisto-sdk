from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.files.file import File


class TestFile:
    def test_read_from_local_path_error(self):
        """
        Given:
         - path that does not exist

        When:
         - Running read_from_local_path method from File object

        Then:
         - make sure ValueError is raised
        """
        with pytest.raises(ValueError):
            File.read_from_local_path("path_does_not_exist")

    def test_read_from_file_content_error(self):
        """
        Given:
         - empty bytes

        When:
         - Running read_from_file_content method from File object

        Then:
         - make sure ValueError is raised
        """
        with pytest.raises(ValueError):
            File.read_from_file_content(b"")

    def test_read_from_http_request_error(self):
        """
        Given:
         - invalid URL

        When:
         - Running read_from_http_request method from File object

        Then:
         - make sure ValueError is raised
        """
        with pytest.raises(ValueError):
            File.read_from_http_request("not/valid/url")

    def test_write_file_error(self):
        """
        Given:
         - invalid path

        When:
         - Running write_file method from File object

        Then:
         - make sure ValueError is raised
        """
        with pytest.raises(ValueError):
            File.write_file({}, output_path="some/path")


class FileTesting(ABC):
    @pytest.fixture()
    @abstractmethod
    def input_files(self, git_repo):
        pass

    @staticmethod
    def get_requests_mock(mocker, path: str):
        import requests

        api_response = requests.Response()
        api_response.status_code = 200
        api_response._content = Path(path).read_bytes()
        return mocker.patch.object(requests, "get", return_value=api_response)

    @abstractmethod
    def test_read_from_local_path(self, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_read_from_local_path_from_content_root(
        self, input_files: Tuple[List[str], str]
    ):
        pass

    @abstractmethod
    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_read_from_github_api(self, mocker, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_read_from_gitlab_api(self, mocker, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_read_from_http_request(self, mocker, input_files: Tuple[List[str], str]):
        pass

    @abstractmethod
    def test_write_file(self, git_repo):
        pass
