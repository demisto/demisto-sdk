import json
import os
from os.path import join
from pathlib import Path

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.tests.test_tools import create_temp_file

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
    os.chdir(join(DEMISTO_SDK_PATH, 'tests', 'integration_tests'))
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[integration_with_secrets_path]
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [SECRETS_CMD], catch_exceptions=False)
    assert result.exit_code == 0
    assert not result.stderr
    assert "no secrets were found" in result.stdout


def test_integration_secrets_integration_with_regex_expression(tmp_path):
    """
    Given
    - White list with a term that can be regex (***.).
    - Content with one secret, the term above    ^^.

    When
    - Removing terms containing that regex

    Then
    - Ensure secrets that the secret isn't in the output.
    - Ensure no error raised
    """
    white_list_path = create_temp_file(tmp_path, json.dumps({"generic_strings": "***.url\n"}), 'whitelist.txt')
    file_contents_path = create_temp_file(tmp_path, '''
    Random and unmeaningful file content
    a string containing ***.url\n
    ''')
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [SECRETS_CMD, '--input', file_contents_path, '-wl', white_list_path], catch_exceptions=False)
    assert result.exit_code == 0
    assert not result.stderr
    assert "no secrets were found" in result.stdout


def test_integration_secrets_integration_positive_with_input_option():
    """
    Given
    - Integration with no secrets in it.
    - Default whitelist (no -wl supplied)

    When
    - Running secrets

    Then
    - Ensure secrets that the secret isn't in the output.
    - Ensure no error raised
    """
    integration_secrets_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml"
    )
    result = CliRunner(mix_stderr=False).invoke(main, [SECRETS_CMD, '--input', integration_secrets_path])
    assert 'Finished validating secrets, no secrets were found' in result.stdout


def test_integration_secrets_integration_negative_with_input_option(tmp_path):
    """
    Given
    - A file containing secret
    - Default whitelist (no -wl supplied)

    When
    - Running secrets

    Then
    - Ensure secrets found.
    """
    integration_secrets_path = create_temp_file(tmp_path, 'ThunderBolt@ndLightningVeryV3ryFr1eghtningM3\n')
    result = CliRunner(mix_stderr=False).invoke(main, [SECRETS_CMD, '--input', integration_secrets_path])
    assert 'Secrets were found in the following files' in result.stdout
