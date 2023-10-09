from pathlib import Path
from typing import List, Tuple

import pytest

from demisto_sdk.commands.common.files.tests.file_test import FileObjectsTesting
from demisto_sdk.commands.common.files.yml_file import YmlFile
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from TestSuite.test_tools import ChangeCWD


class TestYMLFile(FileObjectsTesting):
    @pytest.fixture(autouse=True)
    def input_files(self, git_repo):
        pack = git_repo.create_pack("test")
        integration = pack.create_integration(yml={"test": "test"})
        script = pack.create_script(yml={"test": "test"})
        playbook = pack.create_playbook(yml={"test": "test"})
        modeling_rule = pack.create_modeling_rule(yml={"test": "test"})
        correlation_rule = pack.create_correlation_rule(
            name="test", content={"test": "test"}
        )

        if git_util := git_repo.git_util:
            git_util.commit_files("commit all yml files")

        yml_file_paths = [
            integration.yml.path,
            script.yml.path,
            playbook.yml.path,
            modeling_rule.yml.path,
            correlation_rule.correlation_rule_tmp_path,
        ]
        return yml_file_paths, git_repo.path

    def test_read_from_local_path(self, input_files: Tuple[List[str], str]):
        yml_file_paths, _ = input_files

        for path in yml_file_paths:
            expected_file_content = yaml.load(Path(path).read_text())
            actual_file_content = YmlFile.read_from_local_path(path)
            assert (
                actual_file_content == expected_file_content
            ), f"Could not read text file {path} properly, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_git_path(self, input_files: Tuple[List[str], str]):
        yml_file_paths, git_repo_path = input_files

        with ChangeCWD(git_repo_path):
            for path in yml_file_paths:
                expected_file_content = yaml.load(Path(path).read_text())
                actual_file_content = YmlFile.read_from_git_path(
                    path, from_remote=False
                )
                assert (
                    actual_file_content == expected_file_content
                ), f"Could not read text file {path} properly from git, expected: {expected_file_content}, actual: {actual_file_content}"

    def test_read_from_github_api(self, mocker, input_files: Tuple[List[str], str]):
        pass

    def test_read_from_gitlab_api(self, mocker, input_files: Tuple[List[str], str]):
        pass

    def test_read_from_http_request(self, mocker, input_files: Tuple[List[str], str]):
        pass

    def test_write_file(self, git_repo):
        pass
