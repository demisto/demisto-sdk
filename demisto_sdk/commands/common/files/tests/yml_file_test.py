from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.constants import DEMISTO_GIT_PRIMARY_BRANCH
from demisto_sdk.commands.common.files.errors import LocalFileReadError
from demisto_sdk.commands.common.files.tests.file_test import FileTesting
from demisto_sdk.commands.common.files.yml_file import YmlFile
from demisto_sdk.commands.common.git_content_config import GitContentConfig, GitProvider
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from TestSuite.repo import Repo
from TestSuite.test_tools import ChangeCWD


class TestYMLFile(FileTesting):
    @pytest.fixture()
    def input_files(self, git_repo: Repo):
        file_content = {"test": "test"}
        pack = git_repo.create_pack("test")
        integration = pack.create_integration(yml=file_content)
        script = pack.create_script(yml=file_content)
        playbook = pack.create_playbook(yml=file_content)
        modeling_rule = pack.create_modeling_rule(yml=file_content)
        correlation_rule = pack.create_correlation_rule(
            name="test", content=file_content
        )

        if git_util := git_repo.git_util:
            git_util.commit_files("commit all yml files")

        yml_file_paths = [
            integration.yml.path,
            script.yml.path,
            playbook.yml.path,
            modeling_rule.yml.path,
            correlation_rule.path,
        ]
        return yml_file_paths, git_repo.path

    def test_read_from_local_path(self, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid yml files

        When:
         - Running read_from_local_path method from YmlFile object

        Then:
         - make sure reading the yml files from local file system is successful.
        """
        yml_file_paths, _ = input_files

        for path in yml_file_paths:
            expected_file_content = yaml.load(Path(path).read_text())
            actual_file_content = YmlFile.read_from_local_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read yml file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_local_path_invalid_yml_file_raises_error(self, repo: Repo):
        """
        Given:
         - invalid yml file

        When:
         - Running read_from_local_path method from YmlFile object

        Then:
         - make sure an exception is raised as the file is invalid yml file.
        """
        pack = repo.create_pack()
        pack.pack_ignore.write_text("{'test':'test''}")
        with pytest.raises(LocalFileReadError):
            YmlFile.read_from_local_path(pack.pack_ignore.path)

    def test_read_from_local_path_from_content_root(
        self, input_files: Tuple[List[str], str]
    ):
        """
        Given:
         - relative valid yml file paths

        When:
         - Running read_from_local_path method from YmlFile object and from content root repo

        Then:
         - make sure reading the yml files from local file system is successful
        """
        yml_file_paths, git_repo_path = input_files
        with ChangeCWD(git_repo_path):
            for path in yml_file_paths:
                expected_file_content = yaml.load(Path(path).read_text())
                file_path_from_content_root = GitUtil().path_from_git_root(path)
                actual_file_content = YmlFile.read_from_local_path(
                    file_path_from_content_root
                )
                assert (
                    actual_file_content == expected_file_content
                ), f"Could not read text file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid yml files

        When:
         - Running read_from_git_path method from YmlFile object

        Then:
         - make sure reading the yml files from the master in git is successful.
        """
        yml_file_paths, git_repo_path = input_files

        with ChangeCWD(git_repo_path):
            for path in yml_file_paths:
                expected_file_content = yaml.load(Path(path).read_text())
                actual_file_content = YmlFile.read_from_git_path(
                    path, from_remote=False
                )
                assert (
                    actual_file_content == expected_file_content
                ), f"Could not read yml file {path} properly from git, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_github_api(self, mocker, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid yml files

        When:
         - Running read_from_github_api method from YmlFile object

        Then:
         - make sure reading the yml files from the github api is successful.
        """
        yml_file_paths, _ = input_files
        for path in yml_file_paths:
            requests_mocker = self.get_requests_mock(mocker, path=path)
            assert YmlFile.read_from_github_api(path) == yaml.load(
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
         - valid yml files

        When:
         - Running read_from_gitlab_api method from YmlFile object

        Then:
         - make sure reading the yml files from the gitlab api is successful.
        """
        from urllib.parse import unquote

        yml_file_paths, _ = input_files
        for path in yml_file_paths:
            requests_mocker = self.get_requests_mock(mocker, path=path)
            assert YmlFile.read_from_gitlab_api(
                path,
                git_content_config=GitContentConfig(
                    repo_hostname="test.com",
                    git_provider=GitProvider.GitLab,
                    project_id=1234,
                ),
            ) == yaml.load(Path(path).read_text())
            # make sure that the URL is sent correctly
            assert path in unquote(requests_mocker.call_args.args[0])
            assert requests_mocker.call_args.kwargs["params"] == {
                "ref": DEMISTO_GIT_PRIMARY_BRANCH
            }

    def test_read_from_http_request(self, mocker, input_files: Tuple[List[str], str]):
        """
        Given:
         - valid yml files

        When:
         - Running read_from_http_request method from YmlFile object

        Then:
         - make sure reading the yml files from http request is successful.
        """
        yml_file_paths, _ = input_files
        for path in yml_file_paths:
            self.get_requests_mock(mocker, path=path)
            assert YmlFile.read_from_http_request(path) == yaml.load(
                Path(path).read_text()
            )

    def test_write_file(self, git_repo: Repo):
        """
        Given:
         - yml file path to write

        When:
         - Running write_file method from YmlFile object

        Then:
         - make sure writing yml file is successful.
        """
        _path = Path(git_repo.path) / "file.yml"
        YmlFile.write({"test": "test"}, output_path=_path)
        assert _path.exists()
        assert yaml.load(Path(_path).read_text()) == {"test": "test"}
