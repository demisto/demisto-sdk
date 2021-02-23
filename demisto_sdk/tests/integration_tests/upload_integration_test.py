from os.path import join

import click
import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.legacy_git_tools import git_path
from packaging.version import parse

UPLOAD_CMD = "upload"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")


@pytest.fixture
def demisto_client(mocker):
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.demisto_client",
        return_valure="object"
    )
    mocker.patch("demisto_sdk.commands.upload.uploader.get_demisto_version", return_value=parse('6.0.0'))
    mocker.patch("demisto_sdk.commands.common.content.objects.pack_objects.integration.integration.get_demisto_version",
                 return_value=parse('6.0.0'))
    mocker.patch("demisto_sdk.commands.common.content.objects.pack_objects.script.script.get_demisto_version",
                 return_value=parse('6.0.0'))
    mocker.patch("click.secho")


def test_integration_upload_pack_positive(demisto_client):
    """
    Given
    - Content pack named FeedAzure to upload.

    When
    - Uploading the pack.

    Then
    - Ensure upload runs successfully.
    - Ensure success upload message is printed.
    """

    pack_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure"
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", pack_path, "--insecure"])
    assert result.exit_code == 0
    assert '\nSUCCESSFUL UPLOADS:' in click.secho.call_args_list[3][0][0]
    assert "│ FeedAzure.yml                              │ integration   │" in click.secho.call_args_list[4][0][0]
    assert "│ FeedAzure_test.yml                         │ playbook      │" in click.secho.call_args_list[4][0][0]
    assert "│ just_a_test_script.yml                     │ testscript    │" in click.secho.call_args_list[4][0][0]
    assert "│ playbook-FeedAzure_test_copy_no_prefix.yml │ testplaybook  │" in click.secho.call_args_list[4][0][0]
    assert "│ script-prefixed_automation.yml             │ testscript    │" in click.secho.call_args_list[4][0][0]
    assert "│ FeedAzure_test.yml                         │ testplaybook  │" in click.secho.call_args_list[4][0][0]
    assert "│ incidentfield-city.json                    │ incidentfield │" in click.secho.call_args_list[4][0][0]

    assert not result.stderr


def test_integration_upload_path_does_not_exist(demisto_client):
    """
    Given
    - Directory path which does not exist.

    When
    - Uploading the directory.

    Then
    - Ensure upload fails.
    - Ensure failure upload message is printed.
    """
    invalid_dir_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/DoesNotExist"
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", invalid_dir_path, "--insecure"])
    assert result.exit_code == 1
    assert f"Error: Given input path: {invalid_dir_path} does not exist" in click.secho.call_args_list[1][0][0]
    assert not result.stderr


def test_integration_upload_script_invalid_path(demisto_client, tmp_path):
    """
    Given
    - Directory with invalid path - "Script" instead of "Scripts".

    When
    - Uploading the script.

    Then
    - Ensure upload fails due to invalid path.
    - Ensure failure upload message is printed.
    """
    invalid_scripts_dir = tmp_path / "Script" / "InvalidScript"
    invalid_scripts_dir.mkdir(parents=True)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", str(invalid_scripts_dir), "--insecure"])
    assert result.exit_code == 1
    assert f"""
Error: Given input path: {str(invalid_scripts_dir)} is not uploadable. Input path should point to one of the following:
  1. Pack
  2. A content entity directory that is inside a pack. For example: an Integrations directory or a Layouts directory
  3. Valid file that can be imported to Cortex XSOAR manually. For example a playbook: helloWorld.yml""" in\
        click.secho.call_args_list[1][0][0]
    assert not result.stderr


def test_integration_upload_pack_invalid_connection_params(mocker):
    """
    Given
    - Content pack with "invalid" connection params.

    When
    - Uploading the pack.

    Then
    - Ensure pack is not uploaded and correct error message is printed.
    """

    pack_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure"
    )
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.demisto_client",
        return_valure="object"
    )
    mocker.patch("demisto_sdk.commands.upload.uploader.get_demisto_version", return_value="0")
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", pack_path, "--insecure"])
    assert result.exit_code == 1
    assert "Could not connect to XSOAR server. Try checking your connection configurations." in result.stdout
