from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

VALIDATE_CMD = "validate"
AZURE_FEED_PACK_PATH = join(git_path(), "demisto_sdk/tests/test_files/content_repo_example/Packs/FeedAzure")


def test_integration_validate_incident_field_positive():
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
    assert result.exit_code == 0
    assert "Starting validating files structure" in result.stdout
    assert f"Validating {pack_incident_field_path}" in result.stdout
    assert "The files are valid" in result.stdout
    assert result.stderr == ""


def test_integration_validate_integration_negative():
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
