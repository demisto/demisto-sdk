import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.create_artifacts.tests.content_artifacts_creator_test import (
    destroy_by_ext, duplicate_file, same_folders, temp_dir)
from wcmatch.pathlib import Path

ARTIFACTS_CMD = 'create-content-artifacts'

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
ARTIFACTS_EXPEXTED_RESULTS = TEST_DATA / 'artifacts'


@pytest.fixture()
def mock_git(mocker):
    from demisto_sdk.commands.common.content import Content

    # Mock git working directory
    mocker.patch.object(Content, 'git')
    Content.git().working_tree_dir = TEST_CONTENT_REPO
    yield


def test_integration_create_content_artifacts_no_zip(mock_git):
    expected_artifacts_path = ARTIFACTS_EXPEXTED_RESULTS / 'content'

    with temp_dir() as temp:
        runner = CliRunner()
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '--no-zip'])

        assert same_folders(temp, expected_artifacts_path)
        assert result.exit_code == 0


def test_integration_create_content_artifacts_zip(mock_git):
    with temp_dir() as temp:
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp])

        assert Path(temp / 'content_new.zip').exists()
        assert Path(temp / 'all_content.zip').exists()
        assert Path(temp / 'content_packs.zip').exists()
        assert Path(temp / 'content_test.zip').exists()
        assert result.exit_code == 0


@pytest.mark.parametrize(argnames="suffix", argvalues=["yml", "json"])
def test_malformed_file_failure(mock_git, suffix: str):

    with destroy_by_ext(suffix), temp_dir() as temp:
        runner = CliRunner()
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '--no-zip'])

    assert result.exit_code == 1


def test_duplicate_file_failure(mock_git):
    with duplicate_file(), temp_dir() as temp:
        runner = CliRunner()
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '--no-zip'])

    assert result.exit_code == 1
