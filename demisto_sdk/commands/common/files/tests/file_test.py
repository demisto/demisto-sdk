from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Union

import pytest

from demisto_sdk.commands.common.files import (
    BinaryFile,
    IniFile,
    JsonFile,
    TextFile,
    YmlFile,
)
from demisto_sdk.commands.common.files.errors import UnknownFileError
from demisto_sdk.commands.common.files.file import File
from TestSuite.repo import Repo


class TestFile:
    def test_from_path_valid_json_based_content_items(self, repo: Repo):
        """
        Given:
         - json based content items

        When:
         - Running from_path method

        Then:
         - make sure the returned model is JsonFile
        """
        file_content = {"test": "test"}
        pack = repo.create_pack("test")
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
            assert type(File._from_path(path)) == JsonFile

    def test_from_path_valid_yml_based_content_items(self, repo: Repo):
        """
        Given:
         - yml based content items

        When:
         - Running from_path method

        Then:
         - make sure the returned model is YmlFile
        """
        file_content = {"test": "test"}
        pack = repo.create_pack("test")
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
            assert type(File._from_path(path)) == YmlFile

    def test_from_path_valid_text_based_files(self, repo: Repo):
        """
        Given:
         - text based content items

        When:
         - Running from_path method

        Then:
         - make sure the returned model is TextFile
        """
        pack = repo.create_pack("test")
        integration = pack.create_integration(
            commands_txt="hello-world-command",
            readme="this is the readme",
            description="This is the description",
            code="print('hello_world')",
            test="print('hello_world')",
        )
        release_notes = pack.create_release_notes(
            version="1.1.1", content="\n#### Integrations\n##### test\n- added feature"
        )

        text_file_paths = [
            release_notes.path,
            integration.commands_txt.path,
            integration.readme.path,
            integration.description.path,
            integration.code.path,
            integration.test.path,
        ]

        for path in text_file_paths:
            assert type(File._from_path(path)) == TextFile

    def test_from_path_valid_ini_based_files(self, repo: Repo):
        """
        Given:
         - ini based files

        When:
         - Running from_path method

        Then:
         - make sure the returned model is IniFile
        """
        pack = repo.create_pack()
        pack.pack_ignore.write_list(
            [
                "[file:IntegrationTest.yml]\nignore=IN122,RM110",
            ]
        )
        _ini_file_path = str(Path(repo.path) / "file.ini")

        IniFile.write_file(
            {
                "test": {
                    "test": "1,2,3",
                },
                "test2": {"test1": None},
            },
            output_path=_ini_file_path,
        )

        ini_file_paths = [pack.pack_ignore.path, _ini_file_path]
        for path in ini_file_paths:
            assert type(File._from_path(path)) == IniFile

    def test_from_path_valid_binary_files(self, repo: Repo):
        """
        Given:
         - binary based files

        When:
         - Running from_path method

        Then:
         - make sure the returned model is BinaryFile
        """
        pack = repo.create_pack("test")
        integration = pack.create_integration()
        _bin_file_path = str(Path(repo.path) / "file.bin")
        BinaryFile.write_file("test".encode(), output_path=_bin_file_path)

        binary_file_paths = [integration.image.path, _bin_file_path]
        for path in binary_file_paths:
            assert type(File._from_path(path)) == BinaryFile

    def test_from_path_unknown_file_error(self, repo: Repo):
        """
        Given:
         - file with unknown-suffix

        When:
         - Running from_path method

        Then:
         - make sure UnknownFileError exception is raised
        """
        _path = Path(repo.path) / "file.unknown-suffix"
        TextFile.write_file("text", output_path=_path)
        with pytest.raises(UnknownFileError):
            File._from_path(_path)

    def test_read_from_local_path_error(self):
        """
        Given:
         - path that does not exist

        When:
         - Running read_from_local_path method from File object

        Then:
         - make sure UnknownFileError is raised
        """
        with pytest.raises(UnknownFileError):
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
