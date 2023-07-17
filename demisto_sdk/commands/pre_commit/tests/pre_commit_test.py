from pathlib import Path

import pytest

import demisto_sdk.commands.pre_commit.pre_commit_command as pre_commit_command
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.pre_commit_command import (
    GitUtil,
    group_by_python_version,
    preprocess_files,
    subprocess,
    yaml,
)
from TestSuite.repo import Repo

TEST_DATA_PATH = (
    Path(git_path()) / "demisto_sdk" / "commands" / "pre_commit" / "tests" / "test_data"
)


@pytest.mark.parametrize("is_test", [True, False])
def test_config_files(mocker, repo: Repo, is_test: bool):
    """
    Given:
        A repository with different scripts and integration of different python versions

    When:
        Calling demisto-sdk pre-commit

    Then:
        Categorize the scripts and integration by python version, and make sure that pre-commit configuration is created for each
    """
    mocker.patch.object(
        pre_commit_command,
        "PRECOMMIT_TEMPLATE_PATH",
        TEST_DATA_PATH / ".pre-commit-config_template.yaml",
    )
    pack1 = repo.create_pack("Pack1")
    mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(repo.path))

    integration1 = pack1.create_integration(
        "integration1", docker_image="demisto/python3:3.9.1.14969"
    )
    integration2 = pack1.create_integration(
        "integration2", docker_image="demisto/python3:3.10.2.14969"
    )
    integration3 = pack1.create_integration(
        "integration3", docker_image="demisto/python3:3.8.2.14969"
    )
    script1 = pack1.create_script("script1", docker_image="demisto/python3:2.7.1.14969")
    incident_field = pack1.create_incident_field("incident_field")
    classifier = pack1.create_classifier("classifier")
    mocker.patch.object(yaml, "dump", side_effect=lambda *args: [])
    mock_subprocess = mocker.patch.object(subprocess, "run")
    relative_paths = {
        path.relative_to(repo.path)
        for path in Path(pack1.path).rglob("*")
        if path.is_file()
    }
    mocker.patch.object(
        GitUtil,
        "get_all_files",
        return_value=relative_paths
        | {Path("README.md"), Path("test.md"), Path("fix.md")},
    )
    files_to_run = preprocess_files([Path(pack1.path)])
    assert files_to_run == relative_paths

    pre_commit = pre_commit_command.PreCommitRunner(
        None, group_by_python_version(files_to_run), ""
    )
    assert (
        Path(script1.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["2.7"]
    )
    assert (
        Path(integration3.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.8"]
    )
    assert (
        Path(integration1.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.9"]
    )
    assert (
        Path(integration2.yml.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.10"]
    )
    assert all(
        Path(obj.path).relative_to(repo.path)
        in pre_commit.python_version_to_files["3.10"]
        for obj in (incident_field, classifier)
    )

    pre_commit.run(unit_test=is_test)

    # precommit should not run on python2 files, unless test files
    assert mock_subprocess.call_count == (4 if is_test else 3)

    tests_we_should_skip = {"format", "validate", "secrets", "should_be_skipped"}
    if not is_test:
        tests_we_should_skip.add("run-unit-tests")
    for m in mock_subprocess.call_args_list:
        assert set(m.kwargs["env"]["SKIP"].split(",")) == tests_we_should_skip


@pytest.mark.parametrize("python_version", ["3.8", "3.9", "3.10"])
def test_mypy_hooks(python_version):
    """
    Testing mypy hook created successfully (the python version is correct)
    """
    mypy_hook = {
        "args": [
            "--ignore-missing-imports",
            "--check-untyped-defs",
            "--show-error-codes",
            "--follow-imports=silent",
            "--allow-redefinition",
            "--python-version=3.10",
        ]
    }

    MypyHook(mypy_hook).prepare_hook(python_version)
    assert mypy_hook["args"][-1] == f"--python-version={python_version}"


@pytest.mark.parametrize("python_version", ["3.8", "3.9", "3.10"])
@pytest.mark.parametrize("github_actions", [True, False])
def test_ruff_hook(python_version, github_actions):
    """
    Testing mypy hook created successfully (the python version is correct and github action created successfully)
    """
    ruff_hook = {}
    RuffHook(ruff_hook).prepare_hook(python_version, github_actions)
    python_version_to_ruff = {"3.8": "py38", "3.9": "py39", "3.10": "py310"}
    assert (
        ruff_hook["args"][0]
        == f"--target-version={python_version_to_ruff[python_version]}"
    )
    assert ruff_hook["args"][1] == "--fix"
    if github_actions:
        assert ruff_hook["args"][2] == "--format=github"


class TestPreprocessFiles:
    def test_preprocess_files_with_input_files(self, mocker):
        input_files = [Path("file1.txt"), Path("file2.txt")]
        expected_output = set(input_files)
        mocker.patch.object(GitUtil, "get_all_files", return_value=set(input_files))
        output = preprocess_files(input_files=input_files)
        assert output == expected_output

    def test_preprocess_files_with_staged_only(self, mocker):
        expected_output = set([Path("file1.txt"), Path("file2.txt")])
        mocker.patch.object(GitUtil, "_get_staged_files", return_value=expected_output)
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        output = preprocess_files(staged_only=True)
        assert output == expected_output

    def test_preprocess_files_with_empty_input_files(self):
        input_files = []
        with pytest.raises(ValueError):
            preprocess_files(input_files=input_files)

    def test_preprocess_files_with_nonexistent_files(self, mocker):
        input_files = [Path("file1.txt"), Path("file2.txt"), Path("nonexistent.txt")]
        expected_output = set([Path("file1.txt"), Path("file2.txt")])
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        output = preprocess_files(input_files=input_files)
        assert output == expected_output

    def test_preprocess_files_with_use_git(self, mocker):
        expected_output = set([Path("file1.txt"), Path("file2.txt")])
        mocker.patch.object(
            GitUtil, "_get_all_changed_files", return_value=expected_output
        )
        mocker.patch.object(GitUtil, "_get_staged_files", return_value=set())
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        output = preprocess_files(use_git=True)
        assert output == expected_output

    # Tests that preprocess_files() returns the correct set of Path objects when all_files is True.
    def test_preprocess_files_with_all_files(self, mocker):
        expected_output = set([Path("file1.txt"), Path("file2.txt"), Path("file3.txt")])
        mocker.patch.object(GitUtil, "get_all_files", return_value=expected_output)
        mocker.patch.object(GitUtil, "_get_staged_files", return_value=set())
        output = preprocess_files(all_files=True)
        assert output == expected_output
