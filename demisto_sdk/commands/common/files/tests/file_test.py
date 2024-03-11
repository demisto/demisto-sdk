import os
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
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


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
            assert File._from_path(path) == JsonFile

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
            assert File._from_path(path) == YmlFile

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
            assert File._from_path(path) == TextFile

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

        IniFile.write(
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
            assert File._from_path(path) == IniFile

    def test_read_from_local_path_no_git_reposiotry(self, repo: Repo):
        """
        Given:
         - secrets file
         - no git repository

        When:
         - Running read_from_local_path

        Then:
         - make sure the file is read successfully even when there is no git reposiotry
        """
        secrets_file = repo.create_pack().secrets
        secrets_file.write_secrets(["1.1.1.1"])
        with ChangeCWD(repo.path):
            assert (
                File.read_from_local_path(
                    Path(os.path.relpath(secrets_file.path, repo.path))
                )
                == Path(secrets_file.path).read_text()
            )

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
        BinaryFile.write("test".encode(), output_path=_bin_file_path)

        binary_file_paths = [integration.image.path, _bin_file_path]
        for path in binary_file_paths:
            assert File._from_path(path) == BinaryFile

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
        TextFile.write("text", output_path=_path)
        with pytest.raises(UnknownFileError):
            File._from_path(_path)

    def test_read_from_local_path_file_does_not_exist(self):
        """
        Given:
         - path that does not exist

        When:
         - Running read_from_local_path method from File object

        Then:
         - make sure FileNotFoundError is raised
        """
        with pytest.raises(FileNotFoundError):
            File.read_from_local_path("path_does_not_exist")

    def test_read_from_git_path_file_does_not_exist(self, git_repo: Repo):
        """
        Given:
         - file that does not exist in a master git branch

        When:
         - Running read_from_git_path method from File object

        Then:
         - make sure FileNotFoundError is raised
        """
        with ChangeCWD(git_repo.path):
            with pytest.raises(FileNotFoundError):
                File.read_from_git_path("path_does_not_exist", from_remote=False)

    def test_read_from_http_request_file_does_not_exist(self, requests_mock):
        """
        Given:
         - path that does not exist within an api

        When:
         - Running read_from_http_request method from File object

        Then:
         - make sure FileNotFoundError is raised
        """
        requests_mock.get("https://example.com/file-not-exist.json", status_code=404)
        with pytest.raises(FileNotFoundError):
            File.read_from_http_request("https://example.com/file-not-exist.json")

    def test_read_from_file_content_error(self):
        """
        Given:
         - empty bytes

        When:
         - Running read_from_file_content method from File object

        Then:
         - make sure ValueError is raised as its not possible to automatically identify which File subclass based on the
           file content.
        """
        with pytest.raises(ValueError):
            File.read_from_file_content(b"")

    def test_read_from_local_path(self, repo: Repo):
        """
        Given:
         - local conf json

        When:
         - Running read_from_local_path method from File object

        Then:
         - make sure the conf json is read successfully
        """
        conf_json_path = Path(repo.path) / "Tests/conf.json"
        assert File.read_from_local_path(conf_json_path) == json.loads(
            conf_json_path.read_text()
        )

    def test_read_from_git_path(self, git_repo: Repo):
        """
        Given:
         - a pack with a pack-ignore file in the master branch
         - checking out to a different branch

        When:
         - Running read_from_git_path method from File object

        Then:
         - make sure the pack-ignore is read successfully
        """
        pack = git_repo.create_pack()
        pack.pack_ignore.write_list(
            [
                "[file:IntegrationTest.yml]\nignore=IN122,RM110",
            ]
        )
        git_repo.git_util.commit_files("add pack")
        git_repo.git_util.repo.git.checkout("-b", "some-branch")

        with ChangeCWD(git_repo.path):
            pack_ignore_content = File.read_from_git_path(
                pack.pack_ignore.path, from_remote=False
            )
        assert pack_ignore_content.sections() == ["file:IntegrationTest.yml"]
        assert "ignore" in pack_ignore_content["file:IntegrationTest.yml"]
        assert (
            pack_ignore_content["file:IntegrationTest.yml"]["ignore"] == "IN122,RM110"
        )

    def test_read_from_http_request(self, mocker, repo: Repo):
        """
        Given:
         - integration yml path

        When:
         - Running read_from_http_request method from File object

        Then:
         - make sure the yml file of the integration is read successfully
        """
        import requests

        integration = repo.create_pack().create_integration()

        api_response = requests.Response()
        api_response.status_code = 200
        api_response._content = Path(integration.yml.path).read_bytes()
        mocker.patch.object(requests, "get", return_value=api_response)

        actual_file_content = File.read_from_http_request(integration.yml.path)
        assert isinstance(actual_file_content, dict)
        with Path(integration.yml.path).open("r") as file:
            expected_file_content = yaml.load(file)

        assert actual_file_content == expected_file_content


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
