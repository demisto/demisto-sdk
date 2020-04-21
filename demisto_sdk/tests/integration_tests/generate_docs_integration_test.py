from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

GENERATE_DOCS_COMMAND = 'generate-docs'


def test_unifier_pack():
    """
    Given
    - Valid `city` incident field.

    When
    - Running validation on it.

    Then
    - Ensure validation passes.
    - Ensure success validation message is printed.
    """
    test_file = 'demisto_sdk/tests/test_files/content_repo_example/Packs/FeedAzure/Integrations/FeedAzure/FeedAzure.yml'
    test_file_path = join(git_path(), test_file)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [GENERATE_DOCS_COMMAND, '-i', test_file_path, '--pack'])
    assert result.exit_code == 0
    assert "Merging package:" in result.stdout
    assert "Output file was saved to " in result.stdout
    assert not result.stderr
