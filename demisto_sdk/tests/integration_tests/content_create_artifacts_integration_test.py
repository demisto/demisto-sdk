import os

import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.create_artifacts.tests.content_artifacts_creator_test import (
    destroy_by_ext, duplicate_file, same_folders, temp_dir)
from TestSuite.test_tools import ChangeCWD
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


def test_integration_create_content_artifacts_no_zip(repo):
    expected_artifacts_path = ARTIFACTS_EXPEXTED_RESULTS / 'content'

    with ChangeCWD(repo.path):
        dir_path = repo.make_dir()
        runner = CliRunner()
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', dir_path, '--no-zip'])

        assert same_folders(dir_path, expected_artifacts_path)
        assert result.exit_code == 0


def test_integration_create_content_artifacts_zip(mock_git, repo):
    with ChangeCWD(repo.path):
        dir_path = repo.make_dir()
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [ARTIFACTS_CMD, '-a', dir_path])
        dir_path = Path(dir_path)

        assert Path(dir_path / 'content_new.zip').exists()
        assert Path(dir_path / 'all_content.zip').exists()
        assert Path(dir_path / 'content_packs.zip').exists()
        assert Path(dir_path / 'content_test.zip').exists()
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


def test_specific_pack_creation(repo):
    """Test the -p flag for specific packs creation
    """
    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
        }
    )

    pack_2 = repo.setup_one_pack('Pack2')
    pack_2.pack_metadata.write_json(
        {
            'name': 'Pack Number 2',
        }
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '-p', 'Pack1'])

            assert result.exit_code == 0
            assert os.path.exists(os.path.join(str(temp), 'uploadable_packs', 'Pack1.zip'))
            assert not os.path.exists(os.path.join(str(temp), 'uploadable_packs', 'Pack2.zip'))


def test_all_packs_creation(repo):
    """Test the -p flag for all packs creation
    """
    pack_1 = repo.setup_one_pack('Pack1')
    pack_1.pack_metadata.write_json(
        {
            'name': 'Pack Number 1',
        }
    )

    pack_2 = repo.setup_one_pack('Pack2')
    pack_2.pack_metadata.write_json(
        {
            'name': 'Pack Number 2',
        }
    )

    with ChangeCWD(repo.path):
        with temp_dir() as temp:
            runner = CliRunner(mix_stderr=False)
            result = runner.invoke(main, [ARTIFACTS_CMD, '-a', temp, '-p', 'all'])

            assert result.exit_code == 0
            assert os.path.exists(os.path.join(str(temp), 'uploadable_packs', 'Pack1.zip'))
            assert os.path.exists(os.path.join(str(temp), 'uploadable_packs', 'Pack2.zip'))
