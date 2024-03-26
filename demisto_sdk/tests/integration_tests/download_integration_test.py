import logging
from os.path import join
from pathlib import Path

import pytest
from click.testing import CliRunner
from urllib3.response import HTTPResponse

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.download.tests.downloader_test import Environment
from TestSuite.test_tools import str_in_call_args_list

DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
TEST_FILE_DIR = Path(__file__).parent.parent / "test_files" / "download_command"


def match_request_text(client, url, method, *args, **kwargs):
    if url == "/content/bundle":
        bundle_path = TEST_FILE_DIR / "content_bundle.tar.gz"
        api_response = bundle_path.read_bytes()
        result = HTTPResponse(body=api_response, status=200)

        return result, 200, None

    elif url.startswith("/playbook") and url.endswith("/yaml"):
        filename = url.replace("/playbook/", "").replace("/yaml", "")

        file_path = TEST_FILE_DIR / f"playbook-{filename}.yml"
        api_response = file_path.read_text()

        return api_response, 200, None


@pytest.fixture
def demisto_client(mocker):
    mocker.patch(
        "demisto_sdk.commands.download.downloader.demisto_client",
        return_valure="object",
    )

    mocker.patch(
        "demisto_sdk.commands.download.downloader.demisto_client.generic_request_func",
        side_effect=match_request_text,
    )


def test_integration_download_no_force(demisto_client, tmp_path, mocker):
    """
    Given
    - playbook & script exist in the output pack path.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure no download has been made.
    - Ensure skipped msg is printed.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        main,
        ["download", "-o", pack_path, "-i", "TestScript", "-i", "DummyPlaybook"],
    )
    assert str_in_call_args_list(
        logger_info.call_args_list, "Filtering process completed, 2/13 items remain."
    )
    assert str_in_call_args_list(logger_info.call_args_list, "Skipped downloads: 2")
    assert result.exit_code == 0


def test_integration_download_with_force(demisto_client, tmp_path, mocker):
    """
    Given
    - playbook & script exist in the output pack path.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure download has been made successfully.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        main,
        [
            "download",
            "-o",
            pack_path,
            "-i",
            "TestScript",
            "-i",
            "DummyPlaybook",
            "-f",
        ],
    )
    assert str_in_call_args_list(
        logger_info.call_args_list, "Filtering process completed, 2/13 items remain."
    )
    assert str_in_call_args_list(logger_info.call_args_list, "Successful downloads: 2")
    assert result.exit_code == 0


def test_integration_download_list_files(demisto_client, mocker):
    """
    Given
    - lf flag to list all available content items.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure list files has been made successfully.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, ["download", "-lf"])

    expected_table_str = """Content Name                          Content Type
------------------------------------  ---------------
CommonServerUserPowerShell            script
CommonServerUserPython                script
FormattingPerformance                 script
TestScript                            script
Microsoft Graph Device Management     integration
Symantec Data Loss Prevention (Beta)  betaintegration
Test Integration                      integration
DummyPlaybook                         playbook
FormattingPerformance - Test          playbook
Handle Hello World Alert Test         playbook
MSGraph_DeviceManagement_Test         playbook
Protectwise-Test                      playbook
guy                                   playbook"""

    assert str_in_call_args_list(logger_info.call_args_list, expected_table_str)
    assert result.exit_code == 0


def test_integration_download_fail(demisto_client, tmp_path, mocker):
    """
    Given
    - Script to download, that exists on the machine.
    - Playbook to download, that doesn't exist on the machine.

    When
    - Running demisto-sdk download command.

    Then
    - Ensure that the exit code is 1, since the playbook was not downloaded.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    logger_warning = mocker.patch.object(logging.getLogger("demisto-sdk"), "warning")
    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        main,
        [
            "download",
            "-o",
            pack_path,
            "-i",
            "TestScript",
            "-i",
            "DummyPlaybook1",
            "-f",
        ],
    )
    assert str_in_call_args_list(
        logger_info.call_args_list, "Filtering process completed, 1/13 items remain."
    )
    assert str_in_call_args_list(
        logger_warning.call_args_list,
        "Custom content item 'DummyPlaybook1' provided as an input could not be found / parsed.",
    )
    assert str_in_call_args_list(logger_info.call_args_list, "Successful downloads: 1")
    assert result.exit_code == 1
