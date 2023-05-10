import os
from pathlib import Path

import pytest

import demisto_sdk.commands.pre_commit.pre_commit_command as pre_commit_command
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.pre_commit.hooks.mypy import MypyHook
from demisto_sdk.commands.pre_commit.hooks.ruff import RuffHook
from demisto_sdk.commands.pre_commit.pre_commit_command import (
    YAML_Handler,
    group_by_python_version,
    preprocess_files,
    subprocess,
)
from TestSuite.repo import Repo

TEST_DATA_PATH = (
    Path(git_path()) / "demisto_sdk" / "commands" / "pre_commit" / "tests" / "test_data"
)


yaml = YAML_Handler()


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
    mocker.patch.object(YAML_Handler, "dump", side_effect=lambda *args: [])
    mock_subprocess = mocker.patch.object(subprocess, "run")

    files_to_run = preprocess_files([Path(pack1.path)])
    assert files_to_run == set(Path(pack1.path).rglob("*"))

    pre_commit = pre_commit_command.PreCommitRunner(
        group_by_python_version(files_to_run), ""
    )
    assert Path(script1.yml.path) in pre_commit.python_version_to_files["2.7"]
    assert Path(integration3.yml.path) in pre_commit.python_version_to_files["3.8"]
    assert Path(integration1.yml.path) in pre_commit.python_version_to_files["3.9"]
    assert Path(integration2.yml.path) in pre_commit.python_version_to_files["3.10"]
    assert all(
        Path(obj.path) in pre_commit.python_version_to_files["3.10"]
        for obj in (incident_field, classifier)
    )

    pre_commit.run(unit_test=is_test)

    # precommit should not run on python2 files, unless test files
    assert mock_subprocess.call_count == 3 if not is_test else 4

    tests_we_should_skip = {"format", "validate", "secrets"}
    if not is_test:
        tests_we_should_skip.add("run-unit-tests")
    if os.getenv("CI"):
        tests_we_should_skip.add("update-docker-image")
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
