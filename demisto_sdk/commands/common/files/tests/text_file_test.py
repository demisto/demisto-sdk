import pytest

from demisto_sdk.commands.common.files.tests.file_test import FileReadMethodsTesting
from demisto_sdk.commands.common.files.text_file import TextFile
from demisto_sdk.commands.common.git_util import GitUtil
from TestSuite.test_tools import ChangeCWD


class TestTextFileReadMethods(FileReadMethodsTesting):
    @pytest.fixture(autouse=True)
    def input_files(self, pack):
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
        repo = GitUtil.REPO_CLS.init(pack.repo_path)
        repo.git.add(".")
        repo.index.commit("Initial commit")
        master_branch = repo.create_head("master")
        master_branch.checkout()

        return [
            release_notes,
            integration.commands_txt,
            integration.readme,
            integration.description,
            integration.code,
            integration.test,
        ], pack.repo_path

    @staticmethod
    def run(items, repo, read_method):
        with ChangeCWD(repo):
            for item in items:
                result = read_method(item.path)
                if hasattr(item, "read_text"):
                    assert result == item.read_text()
                elif hasattr(item, "read"):
                    assert result == item.read()

    def test_read_from_local_path(self, input_files):
        items, repo = input_files
        self.run(items, repo, TextFile.read_from_local_path)

    def test_read_from_origin_git_path(self, mocker, input_files):
        mocker.patch.object(
            GitUtil,
            "get_local_remote_file_path",
            side_effect=self.get_local_remote_file_path_side_effect,
        )
        mocker.patch.object(
            GitUtil, "is_file_exist_in_commit_or_branch", return_value=True
        )
        items, repo = input_files
        self.run(items, repo, TextFile.read_from_origin_git_path)

    def test_read_from_local_git_path(self, input_files):
        items, repo = input_files
        self.run(items, repo, TextFile.read_from_local_git_path)
