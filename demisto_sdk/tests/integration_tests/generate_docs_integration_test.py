from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

GENERATE_DOCS_COMMAND = 'generate-docs'


def test_generate_docs_on_file_in_pack():
    """
    Given
    - Valid integration file in pack

    When
    - Running validation on it with --input/-i option

    Then
    - Ensure validation passes.
    - Ensure success validation message is printed.
    """
    test_file = 'demisto_sdk/tests/test_files/content_repo_example/Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml'
    test_file_path = join(git_path(), test_file)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [GENERATE_DOCS_COMMAND, '-i', test_file_path])
    assert result.exit_code == 0
    assert "Merging package:" in result.stdout
    assert "Output file was saved to " in result.stdout
    assert not result.stderr


def test_generate_docs_on_file_not_exists():
    """
    Given
    - None existing file

    When
    - Running validation on non existing file

    Then
    - Ensure validation passes.
    - Ensure success validation message is printed.
    """
    test_file = 'demisto_sdk/tests/test_files/content_repo_example/nofile.yml'
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [GENERATE_DOCS_COMMAND, '-i', test_file])
    assert result.exit_code == 1
    assert 'was not found.' in result.stdout


def test_generate_docs_pack_directory_negative():
    """
    Given
    - A directory with 2 integrations in it

    When
    - Running validation on it with --input/-i option
    - The script can only run on a 1 yml in a directory

    Then
    - Ensure validation fails.
    - Ensure failed message displayed.
    """
    test_file = 'demisto_sdk/tests/test_files/content_repo_example/Packs/FeedAzure/Integrations/FeedAzure/'
    test_file_path = join(git_path(), test_file)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [GENERATE_DOCS_COMMAND, '-i', test_file_path], catch_exceptions=False)
    assert result.exit_code == 0


def test_generate_docs_pack_directory_positive():
    """
    Given
    - A directory with 2 integrations in it

    When
    - Running validation on it with --input/-i option
    - The script can only run on a particular file

    Then
    - Ensure validation fails.
    - Ensure failed message displayed.
    """
    test_file = 'demisto_sdk/tests/test_files/CortexXDR/Integrations/PaloAltoNetworks_XDR'
    test_file_path = join(git_path(), test_file)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [GENERATE_DOCS_COMMAND, '-i', test_file_path])
    assert 0 == result.exit_code
    assert "Output file was saved to " in result.stdout
