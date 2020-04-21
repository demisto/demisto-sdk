import json
from os import chdir
from os.path import join
from pathlib import Path

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

SECRETS_CMD = "secrets"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
SECRETS_WHITELIST = join(DEMISTO_SDK_PATH, "tests/test_files/secrets_white_list.json")


def test_integration_secrets_incident_field_positive(mocker):
    """
    Given
    - Valid `city` incident field.

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation passes.
    - Ensure success secrets validation message is printed.
    """
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[
            join(DEMISTO_SDK_PATH,
                 "tests/test_files/content_repo_example/Packs/FeedAzure/IncidentFields/incidentfield-city.json"
                 )
        ]
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [SECRETS_CMD, '-wl', SECRETS_WHITELIST])
    assert result.exit_code == 0
    assert "Starting secrets detection" in result.output
    assert "Finished validating secrets, no secrets were found." in result.output
    assert result.stderr == ""


def test_integration_secrets_integration_negative(mocker):
    """
    Given
    - FeedAzure integration yml with secrets.

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation fails.
    - Ensure secret strings are in failure message.
    """
    integration_with_secrets_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml"
    )
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[integration_with_secrets_path]
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [SECRETS_CMD, '-wl', SECRETS_WHITELIST])
    assert result.exit_code == 1
    assert "Starting secrets detection" in result.output
    assert "Secrets were found in the following files:" in result.output
    assert f"In File: {integration_with_secrets_path}" in result.stdout
    assert "The following expressions were marked as secrets:" in result.stdout
    assert "feedBypassExclusionList" in result.stdout
    assert "Dynamics365ForMarketingEmail" in result.stdout
    assert "Remove or whitelist secrets in order to proceed, then re-commit" in result.stdout
    assert result.stderr == ""


def test_integration_secrets_integration_positive(mocker, tmp_path):
    """
    Given
    - FeedAzure integration yml with secrets.

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation succeed.
    """
    integration_with_secrets_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml"
    )
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[integration_with_secrets_path]
    )
    whitelist = {
        "iocs": [],
        "urls": [],
        "somethingelse": [],
        "generic_strings": [
            "365ForMarketingEmail",
            "feedBypassExclusionList"
        ]
    }
    whitelist_path = tmp_path / "whitelist.txt"
    whitelist_path.write_text(json.dumps(whitelist))
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [SECRETS_CMD, '-wl', Path(whitelist_path)], catch_exceptions=False)
    assert result.exit_code == 0
    assert not result.stderr
    assert "no secrets were found" in result.stdout


def test_integration_secrets_integration_global_whitelist_positive(mocker):
    """
    Given
    - An integration yml with secrets.
    - Content Repo with whitelist file in it (Tests/secrets_white_list.json)

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation succeed.
    """
    integration_with_secrets_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml"
    )
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[integration_with_secrets_path]
    )
    chdir(join(DEMISTO_SDK_PATH, "tests", "integration_tests"))
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [SECRETS_CMD], catch_exceptions=False)
    assert result.exit_code == 0
    assert not result.stderr
    assert "no secrets were found" in result.stdout
