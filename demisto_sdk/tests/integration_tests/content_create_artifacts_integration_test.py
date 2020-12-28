import logging
import sys

import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.create_artifacts.tests.content_artifacts_creator_test import (
    destroy_by_ext, duplicate_file, same_folders, temp_dir)
from TestSuite.test_tools import ChangeCWD
from wcmatch.pathlib import Path

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

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


def test_test_specific_pack_creation(repo, mocker):
    """Test the -p flag for specific packs creation
    """
    import demisto_sdk.commands.common.logger as logger

    logs_list = []
    log = mock_logging_setup(logs_list)
    mocker.patch.object(logger, 'logging_setup', return_value=log)

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

    full_logs = ''.join([record.msg for record in logs_list])

    assert result.exit_code == 0
    assert 'Pack1' in full_logs
    assert 'Pack2' not in full_logs


def test_all_packs_creation(repo):
    """Test the -p flag for all packs creation
    """

    logs_list = []
    mock_logging_setup(logs_list)

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

    full_logs = ''.join([record.msg for record in logs_list])

    assert result.exit_code == 0
    assert 'Pack1' in full_logs
    assert 'Pack2' in full_logs


def mock_logging_setup(logs_list) -> logging.Logger:
    # Handler class that stores raw LogRecords instances
    class RecordsHandler(logging.Handler):
        # Using list since it's mutable
        def __init__(self, records_list):
            self.records_list = records_list
            super().__init__()

        def emit(self, record):
            self.records_list.append(record)

    logger: logging.Logger = logging.getLogger('demisto-sdk')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.addHandler(RecordsHandler(logs_list))
    logger.propagate = False

    return logger
