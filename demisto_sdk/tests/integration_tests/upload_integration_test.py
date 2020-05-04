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
    assert f"Uploading {pack_path} ..."
    assert f"Merging package: {join(pack_path, 'Integrations/FeedAzure')}" in result.output
    assert "Uploaded integration - 'integration-FeedAzure.yml': successfully" in result.output
    assert "Uploaded playbook - 'just_a_test_script.yml': successfully" in result.output
    assert "Uploaded playbook - 'script-prefixed_automation.yml': successfully" in result.output
    assert "Uploaded playbook - 'playbook-FeedAzure_test_copy_no_prefix.yml': successfully" in result.output
    assert "Uploaded playbook - 'FeedAzure_test.yml': successfully" in result.output
    assert "Uploaded incident field - 'incidentfield-city.json': successfully" in result.output
    assert "UPLOAD SUMMARY:" in result.output
    assert "SUCCESSFUL UPLOADS:" in result.output
    assert "╒════════════════════════════════════════════╤════════════════╕" in result.output
    assert "│ NAME                                       │ TYPE           │" in result.output
    assert "╞════════════════════════════════════════════╪════════════════╡" in result.output
    assert "│ integration-FeedAzure.yml                  │ Integration    │" in result.output
    assert "├────────────────────────────────────────────┼────────────────┤" in result.output
    assert "│ just_a_test_script.yml                     │ Playbook       │" in result.output
    assert "├────────────────────────────────────────────┼────────────────┤" in result.output
    assert "│ script-prefixed_automation.yml             │ Playbook       │" in result.output
    assert "├────────────────────────────────────────────┼────────────────┤" in result.output
    assert "│ playbook-FeedAzure_test_copy_no_prefix.yml │ Playbook       │" in result.output
    assert "├────────────────────────────────────────────┼────────────────┤" in result.output
    assert "│ FeedAzure_test.yml                         │ Playbook       │" in result.output
    assert "├────────────────────────────────────────────┼────────────────┤" in result.output
    assert "│ incidentfield-city.json                    │ Incident Field │" in result.output
    assert "╘════════════════════════════════════════════╧════════════════╛" in result.output
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
    assert f"Error: Given input path: {invalid_dir_path} does not exist" in result.stdout
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
    assert f"\nError: Given input path: {str(invalid_scripts_dir)} is not valid. " \
           f"Input path should point to one of the following:\n" \
           f"  1. Pack\n" \
           f"  2. A content entity directory that is inside a pack. For example: an Integrations directory or a " \
           f"Layouts directory\n" \
           f"  3. Valid file that can be imported to Cortex XSOAR manually. " \
           f"For example a playbook: helloWorld.yml" in result.stdout
    assert not result.stderr
