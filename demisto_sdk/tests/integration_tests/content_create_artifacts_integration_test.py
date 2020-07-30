from filecmp import dircmp

from click.testing import CliRunner
from wcmatch.pathlib import Path
import pytest

from demisto_sdk.__main__ import main
from demisto_sdk.commands.create_artifacts.tests.content_artifacts_creator_test import temp_dir, destroy_by_suffix, duplicate_file

ARTIFACTS_CMD = 'create-content-artifacts'

UNIT_TEST_DATA = (Path(__file__).parent.parent.parent / 'commands' / 'create_artifacts' / 'tests' /
                  'content_artifacts_creator_test' / 'test_create_content_artifacts')
UNIT_TEST_CONTENT_REPO = UNIT_TEST_DATA / 'content'


@pytest.fixture()
def mock_git(mocker):
    from demisto_sdk.commands.common.content.content import Content
    # Mock git working directory
    mocker.patch.object(Content, 'git')
    Content.git().working_tree_dir = UNIT_TEST_CONTENT_REPO
    yield


def test_integration_create_content_artifacts_no_zip(mock_git):
    expected_artifacts_path = UNIT_TEST_DATA / 'content_expected_artifact'

    with temp_dir() as temp:
        runner = CliRunner()
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '--no-zip'])

        assert not dircmp(temp, expected_artifacts_path).diff_files

    assert result.exit_code == 0


def test_integration_create_content_artifacts_zip(mock_git):
    with temp_dir() as temp:
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp])
        assert Path(temp / 'content_new.zip').exists()
        assert Path(temp / 'content_new.zip').exists()
        assert Path(temp / 'content_new.zip').exists()

    assert result.exit_code == 0


@pytest.mark.parametrize(argnames="suffix", argvalues=["yml", "json"])
def test_malformed_file_failure(mock_git, suffix: str):

    with destroy_by_suffix(UNIT_TEST_CONTENT_REPO, suffix), temp_dir() as temp:
        runner = CliRunner()
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '--no-zip'])

    assert result.exit_code == 1


def test_duplicate_file_failure(mock_git):
    with duplicate_file(), temp_dir() as temp:
        runner = CliRunner()
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '--no-zip'])

    assert result.exit_code == 1
