import logging

from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common import tools
from demisto_sdk.commands.common.content.content import Content
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.hook_validations.integration import (
    IntegrationValidator,
)
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list


def test_conf_file_custom(mocker, monkeypatch, repo):
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
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    monkeypatch.setenv("COLUMNS", "1000")

    mocker.patch.object(tools, "is_external_repository", return_value=True)
    mocker.patch.object(IntegrationValidator, "is_valid_category", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value=True)
    mocker.patch.object(Content, "git_util", return_value=GitUtil())
    mocker.patch.object(OldValidateManager, "setup_prev_ver", return_value="origin/master")
    mocker.patch.object(GitUtil, "_is_file_git_ignored", return_value=False)
    pack = repo.create_pack("tempPack")
    integration = pack.create_integration("myInt")
    integration.create_default_integration()
    test_playbook = pack.create_test_playbook("myInt_test_playbook")
    test_playbook.create_default_playbook()
    integration.yml.update({"tests": ["myInt_test_playbook"]})

    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        # pre-conf file - see validate fail on docker related issue
        runner.invoke(main, f"validate -i {integration.yml.path}")
        assert all(
            [
                str_in_call_args_list(
                    logger_info.call_args_list,
                    "================= Validating file ",
                ),
                str_in_call_args_list(
                    logger_info.call_args_list,
                    "DO106",
                ),
            ]
        )

    repo.make_file(".demisto-sdk-conf", "[validate]\nno_docker_checks=True")
    with ChangeCWD(pack.repo_path):
        runner = CliRunner(mix_stderr=False)
        # post-conf file - see validate not fail on docker related issue as we are skipping
        runner.invoke(main, f"validate -i {integration.yml.path}")
        assert all(
            [
                str_in_call_args_list(
                    logger_info.call_args_list,
                    "================= Validating file ",
                ),
                str_in_call_args_list(
                    logger_info.call_args_list,
                    "DO106",
                ),
            ]
        )
