from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.files.tests.file_test import FileObjectsTesting
from demisto_sdk.commands.common.files.text_file import TextFile
from TestSuite.test_tools import ChangeCWD


class TestTextFile(FileObjectsTesting):
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
            with open(path, "r") as file:
                expected_file_content = file.read()

            actual_file_content = TextFile.read_from_local_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read text file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    @pytest.mark.parametrize("from_remote", [True, False])
    def test_read_from_git_path(
        self, mocker, input_files: Tuple[List[str], str], from_remote: bool
    ):

        text_file_paths, git_repo_path = input_files
        with ChangeCWD(git_repo_path):
            for path in text_file_paths:
                with open(path, "r") as file:
                    expected_file_content = file.read()

            actual_file_content = TextFile.read_from_git_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read text file {path} properly from git, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_github_api(self):
        pass

    def test_read_from_gitlab_api(self):
        pass

    def test_read_from_http_request(self):
        pass

    def test_write_file(self):
        pass
