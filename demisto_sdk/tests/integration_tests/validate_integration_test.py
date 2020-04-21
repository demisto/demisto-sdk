from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

VALIDATE_CMD = "validate"
TEST_FILES_PATH = join(git_path(), "demisto_sdk/tests/test_files")
AZURE_FEED_PACK_PATH = join(TEST_FILES_PATH, "content_repo_example/Packs/FeedAzure")


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
    @staticmethod
    def test_negative__non_latest_docker_image():
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
        assert f"{pack_integration_path}: You're not using latest docker for the file, " \
               "please update to latest version." in result.stdout
        assert result.stderr == ""

    @staticmethod
    def test_negative__hidden_param():
        """
        Given
        - Integration with not allowed hidden params.

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

    @staticmethod
    def test_positive__hidden_param():
        """
        Given
        - Integration with allowed hidden params.

        When
        - Running validation on it.
        Then
        - Ensure validation succeeds.
        """
        integration_path = join(TEST_FILES_PATH, 'integration-valid-no-unallowed-hidden-params.yml')
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [VALIDATE_CMD, "-p", integration_path])
        assert_positive(integration_path, result)
