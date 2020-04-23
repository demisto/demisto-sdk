import os
from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

VALIDATE_CMD = "validate"
TEST_FILES_PATH = join(git_path(), "demisto_sdk/tests/test_files/content_repo_example/")
AZURE_FEED_PACK_PATH = "Packs/FeedAzure"
AZURE_FEED_BAD_PACK_METADATA = "Packs/FeedAzure2"
AZURE_FEED_INVALID_PACK_PATH = join(TEST_FILES_PATH, "Packs/FeedAzure")


class TestPack:
    def test_validate_pack(self):
        os.chdir(TEST_FILES_PATH)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", AZURE_FEED_PACK_PATH])
        assert "Starting validating files structure" in result.output
        assert f"Validating Packs/FeedAzure" in result.output
        assert f'Validating Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml' in result.output
        assert f'Validating Packs/FeedAzure/IncidentFields/incidentfield-city.json' in result.output
        assert f'Validating Packs/FeedAzure/TestPlaybooks/FeedAzure_test.yml' in result.output
        assert f'Validating Packs/FeedAzure/TestPlaybooks/script-prefixed_automation.yml' in result.output

    def test_invalid_pack_path(self):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", 'content_repo_example/Packs/FeedAzure'])
        assert result.exit_code == 1
        assert 'content_repo_example/Packs/FeedAzure was not found' in result.output

    def test_pack_metadata(self):
        os.chdir(TEST_FILES_PATH)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", AZURE_FEED_PACK_PATH])
        assert "Validating /Users/sberman/dev/demisto/demisto-sdk/demisto_sdk/tests/test_files/content_repo_" \
               "example/Packs/FeedAzure unique pack files" in result.output
