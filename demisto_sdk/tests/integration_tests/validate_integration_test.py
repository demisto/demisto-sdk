from os.path import join
from subprocess import PIPE, run

from demisto_sdk.commands.common.git_tools import git_path

DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
MAIN_MODULE_PATH = join(DEMISTO_SDK_PATH, "__main__.py")
PYTHON_CMD = "python"
VALIDATE_CMD = "validate"


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
    pack_integration_path = "Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml"
    results = run(
        [PYTHON_CMD, MAIN_MODULE_PATH, VALIDATE_CMD, "-p", pack_integration_path],
        stderr=PIPE,
        stdout=PIPE,
        encoding='utf-8',
        cwd=join(DEMISTO_SDK_PATH, "tests", "test_files", "content_repo_example")
    )
    stdout = results.stdout
    assert "Starting validating files structure" in stdout
    assert f"Validating {pack_integration_path}" in stdout
    assert "The docker image tag is not the latest, please update it" in stdout
    assert f"{pack_integration_path}: You're not using latest docker for the file, " \
           "please update to latest version." in stdout
    assert "The files were found as invalid, the exact error message can be located above" in stdout
    assert results.stderr == ""
    assert results.returncode == 1


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
    pack_incident_field_path = "Packs/FeedAzure/IncidentFields/incidentfield-city.json"
    results = run(
        [PYTHON_CMD, MAIN_MODULE_PATH, VALIDATE_CMD, "-p", pack_incident_field_path],
        stderr=PIPE,
        stdout=PIPE,
        encoding='utf-8',
        cwd=join(DEMISTO_SDK_PATH, "tests", "test_files", "content_repo_example")
    )
    stdout = results.stdout
    assert "Starting validating files structure" in stdout
    assert f"Validating {pack_incident_field_path}" in stdout
    assert "The files are valid" in stdout
    assert results.stderr == ""
    assert results.returncode == 0
