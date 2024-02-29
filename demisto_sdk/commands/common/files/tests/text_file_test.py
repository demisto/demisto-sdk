from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.tests.file_test import FileTesting
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.git_util import GitUtil
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list


class TestTextFile(FileTesting):
    @pytest.fixture()
    def input_files(self, git_repo: Repo):
        pack = git_repo.create_pack("test")
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
        if git_util := git_repo.git_util:
            git_util.commit_files("commit all text files")

        text_file_paths = [
            release_notes.path,
            integration.commands_txt.path,
            integration.readme.path,
            integration.description.path,
            integration.code.path,
            integration.test.path,
        ]
        return text_file_paths, git_repo.path

    def test_read_from_local_path(self, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid text files

        When:
         - Running read_from_local_path method from TextFile object

        Then:
         - make sure reading the text files from local file system is successful.
        """
        text_file_paths, _ = input_files

        for path in text_file_paths:
            expected_file_content = Path(path).read_text()
            actual_file_content = TextFile.read_from_local_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read text file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_local_path_from_content_root(
        self, input_files: Tuple[List[str], str]
    ):
        """
        Given:
         - relative valid text file paths

        When:
         - Running read_from_local_path method from TextFile object and from content root repo

        Then:
         - make sure reading the text files from local file system is successful.
        """
        text_file_paths, git_repo_path = input_files
        with ChangeCWD(git_repo_path):
            for path in text_file_paths:
                expected_file_content = Path(path).read_text()
                file_path_from_content_root = GitUtil().path_from_git_root(path)
                actual_file_content = TextFile.read_from_local_path(
                    file_path_from_content_root
                )
                assert (
                    actual_file_content == expected_file_content
                ), f"Could not read text file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_local_path_unicode_error(self, mocker, repo: Repo):
        """
        Given:
         - text file that is not encoded with utf-8

        When:
         - Running read_from_local_path method from TextFile object

        Then:
         - make sure reading the text file from local file system is successful even when UnicodeDecodeError is raised
        """
        from demisto_sdk.commands.common.logger import logger

        _path = Path(repo.path) / "file"
        debug_logger_mocker = mocker.patch.object(logger, "debug")
        # create a byte sequence that cannot be decoded using utf-8 which represents the char ÿ
        _path.write_bytes(b"\xff")
        assert TextFile.read_from_local_path(_path) == "ÿ"
        assert str_in_call_args_list(
            debug_logger_mocker.call_args_list,
            required_str=f"Error when decoding file {_path} with utf-8",
        )

    def test_read_from_file_content_unicode_error(self, mocker, repo: Repo):
        """
        Given:
         - text file that is not encoded with utf-8

        When:
         - Running read_from_file_content method from TextFile object

        Then:
         - make sure reading the text file from memory is successful even when UnicodeDecodeError is raised
        """
        from demisto_sdk.commands.common.logger import logger

        _path = Path(repo.path) / "file"
        debug_logger_mocker = mocker.patch.object(logger, "debug")
        # create a byte sequence that cannot be decoded using utf-8 which represents the char ÿ
        _path.write_bytes(b"\xff")
        assert TextFile.read_from_file_content(_path.read_bytes()) == "ÿ"
        assert str_in_call_args_list(
            debug_logger_mocker.call_args_list,
            required_str="Error when decoding file when reading it directly from memory",
        )

    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid text files

        When:
         - Running read_from_git_path method from TextFile object

        Then:
         - make sure reading the text files from the master in git is successful.
        """
        text_file_paths, git_repo_path = input_files

        with ChangeCWD(git_repo_path):
            for path in text_file_paths:
                expected_file_content = Path(path).read_text()
                actual_file_content = TextFile.read_from_git_path(
                    path, from_remote=False
                )
                assert (
                    actual_file_content == expected_file_content
                ), f"Could not read text file {path} properly from git, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_github_api(self, mocker, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid text files

        When:
         - Running read_from_github_api method from TextFile object

        Then:
         - make sure reading the text files from the github api is successful.
        """
        text_file_paths, _ = input_files
        for path in text_file_paths:
            requests_mocker = self.get_requests_mock(mocker, path=path)
            assert TextFile.read_from_github_api(path) == Path(path).read_text()
            # make sure that the URL is sent correctly
            assert (
                f"{DEMISTO_GIT_PRIMARY_BRANCH}{path}"
                in requests_mocker.call_args.args[0]
            )

    def test_read_from_gitlab_api(self, mocker, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid text files

        When:
         - Running read_from_gitlab_api method from TextFile object

        Then:
         - make sure reading the text files from the gitlab api is successful.
        """
        from urllib.parse import unquote

        text_file_paths, _ = input_files
        for path in text_file_paths:
            requests_mocker = self.get_requests_mock(mocker, path=path)
            assert (
                TextFile.read_from_gitlab_api(
                    path,
                    git_content_config=GitContentConfig(
                        repo_hostname="test.com",
                        git_provider=GitProvider.GitLab,
                        project_id=1234,
                    ),
                )
                == Path(path).read_text()
            )
            # make sure that the URL is sent correctly
            assert path in unquote(requests_mocker.call_args.args[0])
            assert requests_mocker.call_args.kwargs["params"] == {
                "ref": DEMISTO_GIT_PRIMARY_BRANCH
            }

    def test_read_from_http_request(self, mocker, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid text files

        When:
         - Running read_from_http_request method from TextFile object

        Then:
         - make sure reading the text files from http request is successful.
        """
        text_file_paths, _ = input_files
        for path in text_file_paths:
            self.get_requests_mock(mocker, path=path)
            assert TextFile.read_from_http_request(path) == Path(path).read_text()

    def test_write_file(self, git_repo: Repo):
        """
        Given:
         - text file path to write

        When:
         - Running write_file method from TextFile object

        Then:
         - make sure writing text file is successful.
        """
        _path = Path(git_repo.path) / "file.txt"
        TextFile.write("text", output_path=_path)
        assert _path.exists()
        assert _path.read_text() == "text"
