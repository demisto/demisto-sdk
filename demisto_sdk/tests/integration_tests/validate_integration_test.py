from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.hook_validations.base_validator import \
    BaseValidator

VALIDATE_CMD = "validate"
TEST_FILES_PATH = join(git_path(), "demisto_sdk/tests/test_files")
AZURE_FEED_PACK_PATH = join(TEST_FILES_PATH, "content_repo_example/Packs/FeedAzure")
AZURE_FEED_INVALID_PACK_PATH = join(TEST_FILES_PATH, "content_repo_example/Packs/FeedAzureab")
VALID_PACK_PATH = join(TEST_FILES_PATH, "content_repo_example/Packs/FeedAzureValid")
CONF_JSON_MOCK = {
    "tests": [
        {
            "integrations": "AzureFeed",
            "playbookID": "AzureFeed - Test"
        }
    ]
}


def assert_positive(file_path, result):
    """
    Series of asserts every positive test should do
    :param file_path: path to the file
    :param result: result object as returned from runner.invoke
    """
    assert result.exit_code == 0
    assert "Starting validating files structure" in result.stdout
    assert f"Validating {file_path}" in result.stdout
    assert "The files are valid" in result.stdout
    assert result.stderr == ""


class TestIncidentField:
    def test_positive(self):
        """
        Given
        - Valid `city` incident field.

        When
        - Running validation on it.

        Then
        - Ensure validation passes.
        - Ensure success validation message is printed.
        """
        pack_incident_field_path = join(AZURE_FEED_PACK_PATH, "IncidentFields/incidentfield-city.json")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-p", pack_incident_field_path])
        assert_positive(pack_incident_field_path, result)


class TestIntegration:
    def test_negative__non_latest_docker_image(self):
        """
        Given
        - FeedAzure integration with non-latest docker image.

        When
        - Running validation on it.

        Then
        - Ensure validation fails.
        - Ensure failure message on non-latest docker image.
        """
        pack_integration_path = join(AZURE_FEED_PACK_PATH, "Integrations/FeedAzure/FeedAzure.yml")
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-p", pack_integration_path])
        assert result.exit_code == 1
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {pack_integration_path}" in result.stdout
        assert "The docker image tag is not the latest, please update it" in result.stdout
        assert "You can check for the most updated version of demisto/python3 here:" in result.stdout
        assert result.stderr == ""

    def test_negative__hidden_param(self):
        """
        Given
        - Integration with not allowed hidden params: ["server", "credentials"].

        When
        - Running validation on it.

        Then
        - Ensure validation fails.
        - Ensure failure message on hidden params.
        """
        integration_path = join(TEST_FILES_PATH, 'integration-invalid-no-hidden-params.yml')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-p", integration_path])
        assert result.exit_code == 1
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {integration_path}" in result.stdout
        assert "can't be hidden. Please remove this field" in result.stdout
        assert result.stderr == ""

    def test_positive__hidden_param(self):
        """
        Given
        - Integration with allowed hidden param: "longRunning".

        When
        - Running validation on it.

        Then
        - Ensure validation succeeds.
        """
        integration_path = join(TEST_FILES_PATH, 'integration-valid-no-unallowed-hidden-params.yml')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-p", integration_path])
        assert "Starting validating files structure" in result.stdout
        assert f"Validating {integration_path}" in result.stdout
        assert "can't be hidden. Please remove this field" not in result.stdout
        assert result.stderr == ""


class TestPack:
    def test_integration_validate_pack_positive(self, mocker):
        """
        Given
        - FeedAzure integration valid Pack.

        When
        - Running validation on the pack.

        Then
        - See that the validation succeed.
        """
        mocker.patch.object(BaseValidator, '_load_conf_file', return_value=CONF_JSON_MOCK)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", VALID_PACK_PATH])
        assert "Starting validating files structure" in result.output
        assert f"{VALID_PACK_PATH} unique pack files" in result.output
        assert f"Validating {VALID_PACK_PATH}" in result.output
        assert f"{VALID_PACK_PATH}/Integrations/FeedAzureValid/FeedAzureValid.yml" in result.output
        assert f"{VALID_PACK_PATH}/IncidentFields/incidentfield-city.json" in result.output
        assert "The files are valid" in result.stdout
        assert result.stderr == ""

    def test_integration_validate_pack_negative(self, mocker):
        """
        Given
        - FeedAzure integration invalid Pack with invalid playbook that has unhandled conditional task.

        When
        - Running validation on the pack.

        Then
        - Ensure validation fails.
        - Ensure error message regarding unhandled conditional task in playbook.
        """
        mocker.patch.object(BaseValidator, '_load_conf_file', return_value=CONF_JSON_MOCK)
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", AZURE_FEED_PACK_PATH])
        assert "Starting validating files structure" in result.output
        assert f'{AZURE_FEED_PACK_PATH}' in result.output
        assert f'{AZURE_FEED_PACK_PATH}/IncidentFields/incidentfield-city.json' in result.output
        assert f'{AZURE_FEED_PACK_PATH}/Integrations/FeedAzure/FeedAzure.yml' in result.output
        assert 'Playbook conditional task with id:15 has unhandled condition: #DEFAULT#' in result.output
        assert "The files were found as invalid, the exact error message can be located above" in result.stdout
        assert result.stderr == ""

    def test_integration_validate_invalid_pack_path(self):
        """
        Given
        - FeedAzure integration invalid Pack path.

        When
        - Running validation on the pack.

        Then
        - See that the validation failed.
        """
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-i", AZURE_FEED_INVALID_PACK_PATH])
        assert result.exit_code == 1
        assert f'{AZURE_FEED_INVALID_PACK_PATH} was not found' in result.output
        assert result.stderr == ""
