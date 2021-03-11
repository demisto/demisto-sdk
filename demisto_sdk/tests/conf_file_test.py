from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common import tools
from TestSuite.test_tools import ChangeCWD


def test_conf_file_custom(mocker, repo):
    """
    Given
    - a content repo with a pack and integration.
    - a demisto-sdk-conf file that instructs validate to run on all files and is created mid way in the test.

    When
    - Running validate on the integration file twice - before and after the demisto-sdk-conf file creation.

    Then
    - Ensure validate runs on the specific file when the conf file is not in place.
    - Ensure validate runs on all files after the conf file is in place.
    """
    mocker.patch.object(tools, 'is_external_repository', return_value=True)
    pack = repo.create_pack('tempPack')
    integration = pack.create_integration('myInt')
    integration.create_default_integration()

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        res = runner.invoke(main, f"validate -i {integration.yml.path}")
        assert '================= Validating file =================' in res.stdout
        assert '================= Validating all files =================' not in res.stdout

    repo.make_file('.demisto-sdk-conf', '[validate]\nvalidate_all=True')
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        res = runner.invoke(main, f"validate -i {integration.yml.path}")
        assert '================= Validating file =================' not in res.stdout
        assert '================= Validating all files =================' in res.stdout
