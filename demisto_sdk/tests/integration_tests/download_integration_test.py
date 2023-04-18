import logging
from os.path import join

import pytest
from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.download.tests.downloader_test import Environment
from TestSuite.test_tools import str_in_call_args_list

DOWNLOAD_COMMAND = "download"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")


def match_request_text(client, url, method, response_type="text"):
    if url == "/content/bundle":
        with open(
            "demisto_sdk/tests/test_files/download_command/demisto_api_response"
        ) as f:
            api_response = f.read()

        return (api_response, 200, None)
    elif url.startswith("/playbook") and url.endswith("/yaml"):
        filename = url.replace("/playbook/", "").replace("/yaml", "")
        with open(
            f"demisto_sdk/tests/test_files/download_command/playbook-{filename}.yml"
        ) as f2:
            api_response = f2.read()

            return (api_response, 200, None)


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
    - Ensure force msg is printed.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        main,
        [DOWNLOAD_COMMAND, "-o", pack_path, "-i", "TestScript", "-i", "DummyPlaybook"],
    )
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Demisto instance: Enumerating objects: 2, done.",
                "Demisto instance: Receiving objects: 100% (2/2), done.",
                "Failed to download the following files:",
                "FILE NAME      REASON",
                "-------------  ------------------",
                "TestScript     File already exist",
                "DummyPlaybook  File already exist",
                "To merge existing files use the download command with -f.",
            ]
        ]
    )

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
            DOWNLOAD_COMMAND,
            "-o",
            pack_path,
            "-i",
            "TestScript",
            "-i",
            "DummyPlaybook",
            "-f",
        ],
    )
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Demisto instance: Enumerating objects: 2, done.",
                "Demisto instance: Receiving objects: 100% (2/2), done.",
                '- Merged Script "TestScript"',
                '- Merged Playbook "DummyPlaybook"',
                "2 files merged.",
            ]
        ]
    )
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
    result = runner.invoke(main, [DOWNLOAD_COMMAND, "-lf"])
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "The following files are available to be downloaded from Demisto instance:",
                "FILE NAME                          FILE TYPE",
                "---------------------------------  ------------",
                "Handle Hello World Alert Test      playbook",
                "CommonServerUserPython             script",
                "MSGraph_DeviceManagement_Test      playbook",
                "CommonUserServer                   script",
                "DummyPlaybook                      playbook",
                "Test Integration                   integration",
                "TestScript                         script",
                "Symantec Data Loss Prevention      betaintegration",
                "FormattingPerformance - Test       playbook",
                "CommonServerUserPowerShell         script",
                "Microsoft Graph Device Management  integration",
                "FormattingPerformance              script",
                "Protectwise-Test                   playbook",
                "guy                                playbook",
            ]
        ]
    )
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
    env = Environment(tmp_path)
    pack_path = join(DEMISTO_SDK_PATH, env.PACK_INSTANCE_PATH)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        main,
        [
            DOWNLOAD_COMMAND,
            "-o",
            pack_path,
            "-i",
            "TestScript",
            "-i",
            "DummyPlaybook1",
            "-f",
        ],
    )
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "-----------  ---------------------------------------",
                "DummyPlaybook1  File does not exist in Demisto instance",
            ]
        ]
    )
    assert result.exit_code == 1
