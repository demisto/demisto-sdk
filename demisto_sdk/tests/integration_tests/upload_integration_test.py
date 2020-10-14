from os.path import join

import pytest
from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

UPLOAD_CMD = "upload"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")


@pytest.fixture
def demisto_client(mocker):
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.demisto_client",
        return_valure="object"
    )


def test_integration_upload_pack_positive(demisto_client, mocker):
    """
    Given
    - Content pack named FeedAzure to upload.

    When
    - Uploading the pack.

    Then
    - Ensure upload runs successfully.
    - Ensure success upload message is printed.
    """
    mocker.patch("click.secho")
    from click import secho

    pack_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure"
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", pack_path, "--insecure"])
    assert result.exit_code == 1
    assert '\nSUCCESSFUL UPLOADS:' in secho.call_args_list[2][0][0]
    assert """╒════════════════════════════════════════════╤═════════════╕
│ NAME                                       │ TYPE        │
╞════════════════════════════════════════════╪═════════════╡
│ FeedAzure.yml                              │ Integration │
├────────────────────────────────────────────┼─────────────┤
│ FeedAzure_test.yml                         │ Playbook    │
├────────────────────────────────────────────┼─────────────┤
│ just_a_test_script.yml                     │ Script      │
├────────────────────────────────────────────┼─────────────┤
│ script-prefixed_automation.yml             │ Script      │
├────────────────────────────────────────────┼─────────────┤
│ playbook-FeedAzure_test_copy_no_prefix.yml │ Playbook    │
├────────────────────────────────────────────┼─────────────┤
│ FeedAzure_test.yml                         │ Playbook    │
╘════════════════════════════════════════════╧═════════════╛
""" in secho.call_args_list[3][0][0]
    assert '\nFAILED UPLOADS:' in secho.call_args_list[4][0][0]
    assert """╒═════════════════════════╤═══════════════╤════════════════════════════════════╕
│ NAME                    │ TYPE          │ ERROR                              │
╞═════════════════════════╪═══════════════╪════════════════════════════════════╡
│ incidentfield-city.json │ IncidentField │ Got empty incident field list (52) │
╘═════════════════════════╧═══════════════╧════════════════════════════════════╛
""" in secho.call_args_list[5][0][0]
    assert not result.stderr


def test_integration_upload_path_does_not_exist(demisto_client, mocker):
    """
    Given
    - Directory path which does not exist.

    When
    - Uploading the directory.

    Then
    - Ensure upload fails.
    - Ensure failure upload message is printed.
    """
    mocker.patch("click.secho")
    from click import secho

    invalid_dir_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/DoesNotExist"
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", invalid_dir_path, "--insecure"])
    assert result.exit_code == 1
    assert f"Error: Given input path: {invalid_dir_path} does not exist" in secho.call_args_list[1][0][0]
    assert not result.stderr


def test_integration_upload_script_invalid_path(demisto_client, tmp_path, mocker):
    """
    Given
    - Directory with invalid path - "Script" instead of "Scripts".

    When
    - Uploading the script.

    Then
    - Ensure upload fails due to invalid path.
    - Ensure failure upload message is printed.
    """
    mocker.patch("click.secho")
    from click import secho

    invalid_scripts_dir = tmp_path / "Script" / "InvalidScript"
    invalid_scripts_dir.mkdir(parents=True)
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", str(invalid_scripts_dir), "--insecure"])
    assert result.exit_code == 1
    assert f"""
Error: Given input path: {str(invalid_scripts_dir)} is not valid. Input path should point to one of the following:
  1. Pack
  2. A content entity directory that is inside a pack. For example: an Integrations directory or a Layouts directory
  3. Valid file that can be imported to Cortex XSOAR manually. For example a playbook: helloWorld.yml""" in\
        secho.call_args_list[1][0][0]
    assert not result.stderr
