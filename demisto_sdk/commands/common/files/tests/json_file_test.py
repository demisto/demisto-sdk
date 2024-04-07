from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.errors import LocalFileReadError
from demisto_sdk.commands.common.files.json_file import JsonFile
from demisto_sdk.commands.common.files.tests.file_test import FileTesting
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers.xsoar_handler import JSONDecodeError
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestJsonFile(FileTesting):
    @pytest.fixture()
    def input_files(self, git_repo: Repo):
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
        """
        Given:
         - valid json files

        When:
         - Running read_from_local_path method from JsonFile object

        Then:
         - make sure reading the json files from local file system is successful.
        """
        json_file_paths, _ = input_files

        for path in json_file_paths:
            expected_file_content = json.loads(Path(path).read_text())
            actual_file_content = JsonFile.read_from_local_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read json file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_local_path_invalid_json_file_raises_error(self, repo: Repo):
        """
        Given:
         - invalid json file

        When:
         - Running read_from_local_path method from JsonFile object

        Then:
         - make sure an exception is raised as the file is an invalid json file.
         - make sure json-decoding error was raised
        """
        pack = repo.create_pack()
        with pytest.raises(LocalFileReadError) as exc:
            JsonFile.read_from_local_path(pack.pack_ignore.path)

        assert isinstance(exc.value.original_exc, JSONDecodeError)

    def test_read_from_local_path_from_content_root(
        self, input_files: Tuple[List[str], str]
    ):
        """
        Given:
         - relative valid json file paths

        When:
         - Running read_from_local_path method from JsonFile object and from content root repo

        Then:
         - make sure reading the json files from local file system is successful
        """
        json_file_paths, git_repo_path = input_files
        with ChangeCWD(git_repo_path):
            for path in json_file_paths:
                expected_file_content = json.loads(Path(path).read_text())
                file_path_from_content_root = GitUtil().path_from_git_root(path)
                actual_file_content = JsonFile.read_from_local_path(
                    file_path_from_content_root
                )
                assert (
                    actual_file_content == expected_file_content
                ), f"Could not read text file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid json files

        When:
         - Running read_from_git_path method from JsonFile object

        Then:
         - make sure reading the json files from the master in git is successful.
        """
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
        """
        Given:
         - valid json files

        When:
         - Running read_from_github_api method from JsonFile object

        Then:
         - make sure reading the json files from the github api is successful.
        """
        json_file_paths, _ = input_files
        for path in json_file_paths:
            requests_mocker = self.get_requests_mock(mocker, path=path)
            assert JsonFile.read_from_github_api(path) == json.loads(
                Path(path).read_text()
            )
            # make sure that the URL is sent correctly
            assert (
                f"{DEMISTO_GIT_PRIMARY_BRANCH}{path}"
                in requests_mocker.call_args.args[0]
            )

    def test_read_from_gitlab_api(self, mocker, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid json files

        When:
         - Running read_from_gitlab_api method from JsonFile object

        Then:
         - make sure reading the json files from the gitlab api is successful.
        """
        from urllib.parse import unquote

        json_file_paths, _ = input_files
        for path in json_file_paths:
            requests_mocker = self.get_requests_mock(mocker, path=path)
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
        """
        Given:
         - valid json files

        When:
         - Running read_from_http_request method from JsonFile object

        Then:
         - make sure reading the json files from http request is successful.
        """
        json_file_paths, _ = input_files
        for path in json_file_paths:
            self.get_requests_mock(mocker, path=path)
            assert JsonFile.read_from_http_request(path) == json.loads(
                Path(path).read_text()
            )

    def test_write_file(self, git_repo: Repo):
        """
        Given:
         - json file path to write

        When:
         - Running write_file method from JsonFile object

        Then:
         - make sure writing json file is successful.
        """
        _path = Path(git_repo.path) / "file.json"
        JsonFile.write({"test": "test"}, output_path=_path)
        assert _path.exists()
        assert json.loads(Path(_path).read_text()) == {"test": "test"}
