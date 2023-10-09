from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.tests.file_test import FileTesting
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from TestSuite.test_tools import ChangeCWD


class TestTextFile(FileTesting):
    @pytest.fixture(autouse=True)
    def input_files(self, git_repo):
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

        text_file_paths, _ = input_files

        for path in text_file_paths:
            expected_file_content = Path(path).read_text()
            actual_file_content = TextFile.read_from_local_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read text file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):

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
        import requests

        text_file_paths, _ = input_files
        for path in text_file_paths:
            api_response = requests.Response()
            api_response.status_code = 200
            api_response._content = Path(path).read_bytes()
            requests_mocker = mocker.patch.object(
                requests, "get", return_value=api_response
            )
            assert TextFile.read_from_github_api(path) == Path(path).read_text()
            # make sure that the URL is sent correctly
            assert (
                f"{DEMISTO_GIT_PRIMARY_BRANCH}{path}"
                in requests_mocker.call_args.args[0]
            )

    def test_read_from_gitlab_api(self, mocker, input_files: Tuple[List[str], str]):
        from urllib.parse import unquote

        import requests

        text_file_paths, _ = input_files
        for path in text_file_paths:
            api_response = requests.Response()
            api_response.status_code = 200
            api_response._content = Path(path).read_bytes()
            requests_mocker = mocker.patch.object(
                requests, "get", return_value=api_response
            )
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
        import requests

        text_file_paths, _ = input_files
        for path in text_file_paths:
            api_response = requests.Response()
            api_response.status_code = 200
            api_response._content = Path(path).read_bytes()
            mocker.patch.object(requests, "get", return_value=api_response)
            assert TextFile.read_from_http_request(path) == Path(path).read_text()

    def test_write_file(self, git_repo):
        _path = Path(git_repo.path) / "file.txt"
        TextFile.write_file("text", output_path=_path)
        assert _path.exists()
        assert _path.read_text() == "text"
