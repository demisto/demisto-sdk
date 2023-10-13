from pathlib import Path
from typing import List, Tuple

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.ini_file import IniFile
from demisto_sdk.commands.common.files.tests.file_test import FileTesting
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from TestSuite.test_tools import ChangeCWD


class TestIniFile(FileTesting):
    def input_files(self, git_repo):
        pack = git_repo.create_pack()
        pack.pack_ignore.write_list(
            [
                "[file:IntegrationTest.yml]\nignore=IN122,RM110",
            ]
        )
        _ini_file_path = str(Path(git_repo.path) / "file.ini")

        IniFile.write_file(
            {
                "test": {
                    "test": "1,2,3",
                },
                "test2": {"test1": None},
            },
            output_path=_ini_file_path,
        )

        if git_util := git_repo.git_util:
            git_util.commit_files("commit all INI files")

        ini_file_paths = [pack.pack_ignore.path, _ini_file_path]
        return ini_file_paths, git_repo.path

    def test_read_from_local_path(self, input_files: Tuple[List[str], str]):

        ini_file_paths, _ = input_files

        for path in ini_file_paths:
            actual_file_content = IniFile.read_from_local_path(path)
            assert actual_file_content.sections()

    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):

        ini_file_paths, git_repo_path = input_files

        with ChangeCWD(git_repo_path):
            for path in ini_file_paths:
                actual_file_content = IniFile.read_from_git_path(
                    path, from_remote=False
                )
                assert actual_file_content.sections()

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
            actual_file_content = IniFile.read_from_github_api(path)
            # make sure that the URL is sent correctly
            assert (
                f"{DEMISTO_GIT_PRIMARY_BRANCH}{path}"
                in requests_mocker.call_args.args[0]
            )
            assert actual_file_content.sections()

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
            actual_file_content = IniFile.read_from_gitlab_api(
                path,
                git_content_config=GitContentConfig(
                    repo_hostname="test.com",
                    git_provider=GitProvider.GitLab,
                    project_id=1234,
                ),
            )

            assert actual_file_content.sections()
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
            actual_file_content = IniFile.read_from_http_request(path)
            assert actual_file_content.sections()

    def test_write_file(self, git_repo):
        _path = Path(git_repo.path) / "file.ini"
        IniFile.write_file(
            {
                "test": {
                    "test": "1,2,3",
                },
                "test2": {"test1": None},
            },
            output_path=_path,
        )
        assert _path.exists()
        assert _path.read_text() == "[test]\ntest=1,2,3\n\n[test2]\ntest1\n\n"
