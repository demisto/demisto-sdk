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
    test_playbook = pack.create_test_playbook('myInt_test_playbook')
    test_playbook.create_default_playbook()
    integration.yml.update({'tests': ['myInt_test_playbook']})

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        # pre-conf file - see validate fail on docker related issue
        res = runner.invoke(main, f"validate -i {integration.yml.path}")
        assert '================= Validating file =================' in res.stdout
        assert 'DO106' in res.stdout

    repo.make_file('.demisto-sdk-conf', '[validate]\nno_docker_checks=True')
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        # post-conf file - see validate not fail on docker related issue as we are skipping
        res = runner.invoke(main, f"validate -i {integration.yml.path}")
        assert '================= Validating file =================' in res.stdout
        assert 'DO106' not in res.stdout
