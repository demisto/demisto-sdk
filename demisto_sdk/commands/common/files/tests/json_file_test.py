from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.files.tests.file_test import FileTesting
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from TestSuite.test_tools import ChangeCWD


class TestJsonFile(FileTesting):
    @pytest.fixture()
    def input_files(self, git_repo):
        file_content = {"test": "test"}
        pack = git_repo.create_pack("test")
        indicator_field = pack.create_indicator_field("test", content=file_content)
        indicator_type = pack.create_indicator_type("test", content=file_content)
        incident_field = pack.create_incident_field("test", content=file_content)
        incident_type = pack.create_incident_type("test", content=file_content)
        layout = pack.create_layout("test", content=file_content)
        _list = pack.create_list("test", content=file_content)

        if git_util := git_repo.git_util:
            git_util.commit_files("commit all json files")

        json_file_paths = [
            indicator_field.path,
            indicator_type.path,
            incident_field.path,
            incident_type.path,
            layout.path,
            _list.path,
        ]
        return json_file_paths, git_repo.path

    def test_read_from_local_path(self, input_files: Tuple[List[str], str]):
        json_file_paths, _ = input_files

        for path in json_file_paths:
            expected_file_content = json.loads(Path(path).read_text())
            actual_file_content = JsonFile.read_from_local_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read json file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):
        json_file_paths, git_repo_path = input_files

        with ChangeCWD(git_repo_path):
            for path in json_file_paths:
                expected_file_content = json.loads(Path(path).read_text())
                actual_file_content = JsonFile.read_from_git_path(
                    path, from_remote=False
                )
                assert (
                    actual_file_content == expected_file_content
                ), f"Could not read json file {path} properly from git, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_github_api(self, mocker, input_files: Tuple[List[str], str]):
        import requests

        json_file_paths, _ = input_files
        for path in json_file_paths:
            api_response = requests.Response()
            api_response.status_code = 200
            api_response._content = Path(path).read_bytes()
            requests_mocker = mocker.patch.object(
                requests, "get", return_value=api_response
            )
            assert JsonFile.read_from_github_api(path) == json.loads(
                Path(path).read_text()
            )
            # make sure that the URL is sent correctly
            assert (
                f"{DEMISTO_GIT_PRIMARY_BRANCH}{path}"
                in requests_mocker.call_args.args[0]
            )

    def test_read_from_gitlab_api(self, mocker, input_files: Tuple[List[str], str]):
        from urllib.parse import unquote

        import requests

        json_file_paths, _ = input_files
        for path in json_file_paths:
            api_response = requests.Response()
            api_response.status_code = 200
            api_response._content = Path(path).read_bytes()
            requests_mocker = mocker.patch.object(
                requests, "get", return_value=api_response
            )
            assert JsonFile.read_from_gitlab_api(
                path,
                git_content_config=GitContentConfig(
                    repo_hostname="test.com",
                    git_provider=GitProvider.GitLab,
                    project_id=1234,
                ),
            ) == json.loads(Path(path).read_text())
            # make sure that the URL is sent correctly
            assert path in unquote(requests_mocker.call_args.args[0])
            assert requests_mocker.call_args.kwargs["params"] == {
                "ref": DEMISTO_GIT_PRIMARY_BRANCH
            }

    def test_read_from_http_request(self, mocker, input_files: Tuple[List[str], str]):
        import requests

        json_file_paths, _ = input_files
        for path in json_file_paths:
            api_response = requests.Response()
            api_response.status_code = 200
            api_response._content = Path(path).read_bytes()
            mocker.patch.object(requests, "get", return_value=api_response)
            assert JsonFile.read_from_http_request(path) == json.loads(
                Path(path).read_text()
            )

    def test_write_file(self, git_repo):
        _path = Path(git_repo.path) / "file.yml"
        JsonFile.write_file({"test": "test"}, output_path=_path)
        assert _path.exists()
        assert json.loads(Path(_path).read_text()) == {"test": "test"}
