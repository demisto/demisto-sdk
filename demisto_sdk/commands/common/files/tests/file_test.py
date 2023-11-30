from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Union

import pytest

from demisto_sdk.commands.common.files import JsonFile, YmlFile
from demisto_sdk.commands.common.files.file import File
from TestSuite.repo import Repo


class TestFile:
    def test_from_path_valid_json_based_content_items(self, git_repo: Repo):
        """
        Given:
         - json based content items

        When:
         - Running from_path method

        Then:
         - make sure the returned model is JsonFile
        """
        file_content = {"test": "test"}
        pack = git_repo.create_pack("test")
        indicator_field = pack.create_indicator_field("test", content=file_content)
        indicator_type = pack.create_indicator_type("test", content=file_content)
        incident_field = pack.create_incident_field("test", content=file_content)
        incident_type = pack.create_incident_type("test", content=file_content)
        layout = pack.create_layout("test", content=file_content)
        _list = pack.create_list("test", content=file_content)

        json_file_paths = [
            indicator_field.path,
            indicator_type.path,
            incident_field.path,
            incident_type.path,
            layout.path,
            _list.path,
        ]

        for path in json_file_paths:
            assert type(File.from_path(path)) == JsonFile

    def test_from_path_valid_yml_based_content_items(self, git_repo: Repo):
        """
        Given:
         - yml based content items

        When:
         - Running from_path method

        Then:
         - make sure the returned model is YmlFile
        """
        file_content = {"test": "test"}
        pack = git_repo.create_pack("test")
        integration = pack.create_integration(yml=file_content)
        script = pack.create_script(yml=file_content)
        playbook = pack.create_playbook(yml=file_content)
        modeling_rule = pack.create_modeling_rule(yml=file_content)
        correlation_rule = pack.create_correlation_rule(
            name="test", content=file_content
        )

        yml_file_paths = [
            integration.yml.path,
            script.yml.path,
            playbook.yml.path,
            modeling_rule.yml.path,
            correlation_rule.path,
        ]

        for path in yml_file_paths:
            assert type(File.from_path(path)) == YmlFile

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
    def get_requests_mock(mocker, path: Union[str, Path]):
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
