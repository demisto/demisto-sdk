import pytest
from TestSuite.repo import Repo
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.pre_commit.pre_commit_command import (
    preprocess_files,
    categorize_files,
    YAML_Handler,
    subprocess,
)
from pathlib import Path
import demisto_sdk.commands.pre_commit.pre_commit_command as pre_commit_command

TEST_DATA_PATH = Path(git_path()) / "demisto_sdk" / "commands" / "pre_commit" / "tests" / "test_data"


yaml = YAML_Handler()

@pytest.mark.parametrize("is_test", [True, False])
def test_config_files(mocker, repo: Repo, is_test: bool):
    pack1 = repo.create_pack("Pack1")
    Path(pack1.path).rglob("*")
    mocker.patch.object(pre_commit_command, "CONTENT_PATH", Path(repo.path))

    integration1 = pack1.create_integration("integration1", docker_image="demisto/python3:3.9.1.14969")
    integration2 = pack1.create_integration("integration2", docker_image="demisto/python3:3.10.2.14969")
    integration3 = pack1.create_integration("integration3", docker_image="demisto/python3:3.8.2.14969")
    script1 = pack1.create_script("script1", docker_image="demisto/python3:2.7.1.14969")
    incident_field = pack1.create_incident_field("incident_field")
    classifier = pack1.create_classifier("classifier")
    mock_dump = mocker.patch.object(YAML_Handler, "dump", side_effect=lambda *args: [])
    mock_subprocess = mocker.patch.object(subprocess, "run")

    files_to_run = preprocess_files([Path(pack1.path)])
    assert files_to_run == set(Path(pack1.path).rglob("*"))

    pre_commit = categorize_files(files_to_run)
    assert Path(script1.yml.path) in pre_commit.python_version_to_files["2.7"]
    assert Path(integration3.yml.path) in pre_commit.python_version_to_files["3.8"]
    assert Path(integration1.yml.path) in pre_commit.python_version_to_files["3.9"]
    assert Path(integration2.yml.path) in pre_commit.python_version_to_files["3.10"]
    assert all(Path(obj.path) in pre_commit.python_version_to_files["3.10"] for obj in (incident_field, classifier))

    pre_commit.run(test=is_test)

    # precommit should not run on python2 files, unless test files
    assert mock_dump.call_count == mock_subprocess.call_count == 3 if is_test else 4
    with open(TEST_DATA_PATH / "pre_commit_config_3.8.yml") as f:
        expected_py38_config = yaml.load(f)
    with open(TEST_DATA_PATH / "pre_commit_config_3.9.yml") as f:
        expected_py39_config = yaml.load(f)
    with open(TEST_DATA_PATH / "pre_commit_config_3.10.yml") as f:
        expected_py310_config = yaml.load(f)
    for m in mock_dump.call_args_list:
        assert m[0][0] in (expected_py38_config, expected_py39_config, expected_py310_config)

    should_skip = {"format", "validate"}
    if is_test:
        should_skip.add("run-unit-tests")
    for m in mock_subprocess.call_args_list:
        assert set(m.kwargs["env"]["SKIP"].split(",")) == should_skip
