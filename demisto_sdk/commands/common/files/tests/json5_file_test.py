from pathlib import Path
from typing import Tuple

import pytest

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.json5_file import Json5File
from demisto_sdk.commands.common.files.tests.file_test import FileTesting
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_JSON5_HANDLER as json5
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestJson5File(FileTesting):
    @pytest.fixture()
    def input_files(self, git_repo: Repo):
        json5_file_path = Path(git_repo.path) / "test.json5"
        Json5File.write({"test": "test"}, output_path=json5_file_path)

        if git_util := git_repo.git_util:
            git_util.commit_files("commit all json5 files")

        return json5_file_path, git_repo.path

    def test_read_from_local_path(self, input_files: Tuple[Path, str]):
        """
        Given:
         - valid json5 file

        When:
         - Running read_from_local_path method from Json5File object

        Then:
         - make sure reading the json5 file from local file system is successful.
        """
        json5_file_path, _ = input_files

        expected_file_content = json5.loads(json5_file_path.read_text())
        actual_file_content = Json5File.read_from_local_path(json5_file_path)
        assert (
            actual_file_content == expected_file_content
        ), f"Could not read json file {json5_file_path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_local_path_from_content_root(
        self, input_files: Tuple[Path, str]
    ):
        """
        Given:
         - valid json5 file

        When:
         - Running read_from_local_path method from Json5File object and from content root repo

        Then:
         - make sure reading the json5 file from local file system is successful
        """
        json5_file_path, git_repo_path = input_files
        with ChangeCWD(git_repo_path):
            expected_file_content = json5.loads(json5_file_path.read_text())
            file_path_from_content_root = GitUtil().path_from_git_root(json5_file_path)
            actual_file_content = Json5File.read_from_local_path(
                file_path_from_content_root
            )
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read text file {json5_file_path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_git_path(self, input_files: Tuple[Path, str]):
        """
        Given:
         - valid json5 file

        When:
         - Running read_from_git_path method from Json5File object

        Then:
         - make sure reading the json5 file from the master in git is successful.
        """
        json5_file_path, git_repo_path = input_files

        with ChangeCWD(git_repo_path):
            expected_file_content = json5.loads(json5_file_path.read_text())
            actual_file_content = Json5File.read_from_git_path(
                json5_file_path, from_remote=False
            )
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read json file {json5_file_path} properly from git, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_github_api(self, mocker, input_files: Tuple[Path, str]):
        """
        Given:
         - valid json5 file

        When:
         - Running read_from_github_api method from Json5File object

        Then:
         - make sure reading the json5 file from the github api is successful.
        """
        json5_file_path, _ = input_files
        requests_mocker = self.get_requests_mock(mocker, path=json5_file_path)
        assert Json5File.read_from_github_api(str(json5_file_path)) == json5.loads(
            Path(json5_file_path).read_text()
        )
        # make sure that the URL is sent correctly
        assert (
            f"{DEMISTO_GIT_PRIMARY_BRANCH}{json5_file_path}"
            in requests_mocker.call_args.args[0]
        )

    def test_read_from_gitlab_api(self, mocker, input_files: Tuple[Path, str]):
        """
        Given:
         - valid json5 file

        When:
         - Running read_from_gitlab_api method from Json5File object

        Then:
         - make sure reading the json5 file from the gitlab api is successful.
        """
        from urllib.parse import unquote

        json5_file_path, _ = input_files
        requests_mocker = self.get_requests_mock(mocker, path=json5_file_path)
        assert Json5File.read_from_gitlab_api(
            str(json5_file_path),
            git_content_config=GitContentConfig(
                repo_hostname="test.com",
                git_provider=GitProvider.GitLab,
                project_id=1234,
            ),
        ) == json5.loads(json5_file_path.read_text())
        # make sure that the URL is sent correctly
        assert str(json5_file_path) in unquote(requests_mocker.call_args.args[0])
        assert requests_mocker.call_args.kwargs["params"] == {
            "ref": DEMISTO_GIT_PRIMARY_BRANCH
        }

    def test_read_from_http_request(self, mocker, input_files: Tuple[Path, str]):
        """
        Given:
         - valid json5 file

        When:
         - Running read_from_http_request method from Json5File object

        Then:
         - make sure reading the json5 file from http request is successful.
        """
        json5_file_path, _ = input_files
        self.get_requests_mock(mocker, path=json5_file_path)
        assert Json5File.read_from_http_request(str(json5_file_path)) == json5.loads(
            Path(json5_file_path).read_text()
        )

    def test_write_file(self, git_repo: Repo):
        """
        Given:
         - json5 file path to write

        When:
         - Running write_file method from Json5File object

        Then:
         - make sure writing json5 file is successful.
        """
        _path = Path(git_repo.path) / "file.json5"
        Json5File.write({"test": "test"}, output_path=_path)
        assert _path.exists()
        assert json5.loads(Path(_path).read_text()) == {"test": "test"}
