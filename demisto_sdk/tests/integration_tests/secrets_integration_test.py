import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.secrets.secrets import SecretsValidator
from TestSuite.test_tools import ChangeCWD

SECRETS_CMD = "secrets"


def mock_git(mocker, is_merge: bool = False):
    mocker.patch.object(SecretsValidator, 'get_branch_name', return_value='branch name')
    mocker.patch('demisto_sdk.commands.secrets.secrets.run_command', return_value=is_merge)


def test_integration_secrets_incident_field_positive(mocker, repo):
    """
    Given
    - Valid yml file

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation passes.
    - Ensure success secrets validation message is printed.
    """
    # Mocking the git functionality (Else it'll raise an error)
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    mock_git(mocker)
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[
            integration.yml.rel_path
        ]
    )
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SECRETS_CMD, '-wl', repo.secrets.path])
    assert "Starting secrets detection" in result.output
    assert "Finished validating secrets, no secrets were found." in result.output
    assert result.exit_code == 0
    assert result.stderr == ""


@pytest.mark.skip(reason='Dropped entropy so the secret is now passing')
def test_integration_secrets_integration_negative(mocker, repo):
    """
    Given
    - Integration yml with secrets.

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation fails.
    - Ensure secret strings are in failure message.
    """
    # Mocking the git functionality (Else it'll raise an error)
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('sample')
    mock_git(mocker)
    # Change working dir to repo
    secret_string = 'Dynamics365ForMarketingEmail'
    integration.yml.write({'this is a secrets': secret_string})
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[integration.yml.rel_path]
    )
    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SECRETS_CMD, '-wl', repo.secrets.path])
    assert "Starting secrets detection" in result.output
    assert "Secrets were found in the following files:" in result.output
    assert f"In File: {integration.yml.rel_path}" in result.stdout
    assert "The following expressions were marked as secrets:" in result.stdout
    assert secret_string in result.stdout
    assert "Remove or whitelist secrets in order to proceed, then re-commit" in result.stdout
    assert result.stderr == ""
    assert result.exit_code == 1


def test_integration_secrets_integration_positive(mocker, repo):
    """
    Given
    - FeedAzure integration yml with secrets.

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation succeed.
    """
    # Mocking the git functionality (Else it'll raise an error)
    mock_git(mocker)
    # Change working dir to repo
    pack = repo.create_pack('PackName')
    integration = pack.create_integration('sample')
    secret_string = 'email@white.listed'
    integration.yml.update_description(secret_string)
    repo.secrets.write_secrets(
        generic_strings=[
            secret_string
        ])
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[integration.code.rel_path]
    )
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SECRETS_CMD, '-wl', repo.secrets.path], catch_exceptions=False)
    assert 0 == result.exit_code
    assert not result.stderr
    assert "no secrets were found" in result.stdout


def test_integration_secrets_integration_global_whitelist_positive_using_git(mocker, repo):
    """
    Given
    - An integration yml with secrets.
    - Content Repo with whitelist file in it (Tests/secrets_white_list.json)

    When
    - Running secrets validation on it.

    Then
    - Ensure secrets validation succeed.
    """
    # Mocking the git functionality (Else it'll raise an error)
    pack = repo.create_pack('pack')
    integration = pack.create_integration('integration')
    mock_git(mocker)
    # Mock git diff
    mocker.patch(
        "demisto_sdk.__main__.SecretsValidator.get_all_diff_text_files",
        return_value=[integration.code.rel_path]
    )
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SECRETS_CMD], catch_exceptions=False)
    assert result.exit_code == 0
    assert not result.stderr
    assert "no secrets were found" in result.stdout


def test_integration_secrets_integration_with_regex_expression(mocker, pack):
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
    # Mocking the git functionality (Else it'll raise an error)
    mock_git(mocker)
    pack.secrets.write_secrets('***.url\n')
    integration = pack.create_integration('sample_integration')
    # Can used from integrations list
    integration.code.write('''
    Random and unmeaningful file content
    a string containing ***.url\n
    ''')
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [SECRETS_CMD, '--input', integration.code.rel_path],
                               catch_exceptions=False)
    assert result.exit_code == 0
    assert not result.stderr
    assert "no secrets were found" in result.stdout


def test_integration_secrets_integration_positive_with_input_option(mocker, repo):
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
    # Mocking the git functionality (Else it'll raise an error)
    mock_git(mocker)
    # Create a pack
    pack = repo.create_pack(name='sample_pack')
    integration = pack.create_integration('sample_integration')
    integration.code.write('text that should not get caught')
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        result = CliRunner(mix_stderr=False).invoke(main, [SECRETS_CMD, '--input', integration.code.rel_path])
    assert 'Finished validating secrets, no secrets were found' in result.stdout


def test_integration_secrets_integration_negative_with_input_option(mocker, repo):
    """
    Given
    - A py code related to an integration.
    - Default whitelist (no -wl supplied)

    When
    - Running secrets

    Then
    - Ensure secrets found.
    """
    # Mocking the git functionality (Else it'll raise an error)
    mock_git(mocker)
    pack = repo.create_pack('sample_pack')
    integration = pack.create_integration('sample_integration')
    integration.code.write('email@not.whitlisted\n')
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        result = CliRunner(mix_stderr=False).invoke(main, [SECRETS_CMD, '--input', integration.code.rel_path])
    assert 'Secrets were found in the following files' in result.stdout


def test_integration_secrets_integration_negative_with_input_option_and_whitelist(mocker, repo):
    """
    Given
    - A file containing secret
    - Generic whitelist (empty)

    When
    - Running secrets

    Then
    - Ensure secrets found.
    """
    # Mocking the git functionality (Else it'll raise an error)
    mock_git(mocker)
    pack = repo.create_pack('pack')
    integration = pack.create_integration()
    integration.code.write('email@not.whitlisted\n')
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        result = CliRunner().invoke(main, [SECRETS_CMD, '--input', integration.code.rel_path, '-wl', repo.secrets.path])
    assert 1 == result.exit_code
    assert 'Secrets were found in the following files' in result.stdout


def test_secrets_for_file_name_with_space_in_it(mocker, repo):
    # Mocking the git functionality (Else it'll raise an error)
    mock_git(mocker)
    pack = repo.create_pack('pack')
    integration = pack.create_integration('with space')
    integration.code.write('email@not.whitlisted\n')
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        result = CliRunner().invoke(main, [SECRETS_CMD, '--input', integration.code.rel_path, '-wl', repo.secrets.path])
    assert 1 == result.exit_code
    assert 'Secrets were found in the following files' in result.stdout
