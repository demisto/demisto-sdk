import os

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from TestSuite.test_tools import ChangeCWD

FIND_DEPENDENCIES_CMD = "find-dependencies"


def test_integration_find_dependencies__sanity(mocker, repo):
    """
    Given
    - Valid pack folder

    When
    - Running find-dependencies on it.

    Then
    - Ensure find-dependencies passes.
    - Ensure find-dependencies is printed.
    """
    # Mocking the git functionality (Else it'll raise an error)
    pack = repo.create_pack('FindDependencyPack')
    integration = pack.create_integration('integration')
    mocker.patch(
        "demisto_sdk.commands.find_dependencies.find_dependencies.update_pack_metadata_with_dependencies",
    )
    # Change working dir to repo
    with ChangeCWD(integration.repo_path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [FIND_DEPENDENCIES_CMD,
                                      '-p', os.path.basename(repo.packs[0].path),
                                      '-v', os.path.join(repo.path, 'debug.md'),
                                      ])
    assert 'Found dependencies result for FindDependencyPack pack:' in result.output
    assert "{}" in result.output
    assert result.exit_code == 0
    assert result.stderr == ""
