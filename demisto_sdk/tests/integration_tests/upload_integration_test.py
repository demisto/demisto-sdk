from os.path import join

from click.testing import CliRunner
from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_tools import git_path

UPLOAD_CMD = "upload"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")


def test_integration_upload_pack_positive(mocker):
    """
    Given
    - Content pack named FeedAzure to upload.

    When
    - Uploading the pack.

    Then
    - Ensure upload runs successfully.
    - Ensure success upload message is printed.
    """
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.demisto_client",
        return_valure="object"
    )
    pack_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure"
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", pack_path, "--insecure"])
    assert result.exit_code == 0
    assert f"Uploading {pack_path} ..."
    assert f"Merging package: {join(pack_path, 'Integrations/FeedAzure')}" in result.output
    assert "Uploaded integration: 'integration-FeedAzure.yml' - successfully" in result.output
    assert "Uploaded playbook - 'just_a_test_script.yml' - successfully" in result.output
    assert "Uploaded playbook - 'script-prefixed_automation.yml' - successfully" in result.output
    assert "Uploaded playbook - 'playbook-FeedAzure_test_copy_no_prefix.yml' - successfully" in result.output
    assert "Uploaded playbook - 'FeedAzure_test.yml' - successfully" in result.output
    assert "Uploaded incident field - 'incidentfield-city.json' - successfully" in result.output
    assert "UPLOAD SUMMARY:" in result.output
    assert "SUCCESSFUL UPLOADS:" in result.output
    assert """╒════════════════════════════════════════════╤════════════════╕
│ NAME                                       │ TYPE           │
╞════════════════════════════════════════════╪════════════════╡
│ integration-FeedAzure.yml                  │ Integration    │
├────────────────────────────────────────────┼────────────────┤
│ just_a_test_script.yml                     │ Playbook       │
├────────────────────────────────────────────┼────────────────┤
│ script-prefixed_automation.yml             │ Playbook       │
├────────────────────────────────────────────┼────────────────┤
│ playbook-FeedAzure_test_copy_no_prefix.yml │ Playbook       │
├────────────────────────────────────────────┼────────────────┤
│ FeedAzure_test.yml                         │ Playbook       │
├────────────────────────────────────────────┼────────────────┤
│ incidentfield-city.json                    │ Incident Field │
╘════════════════════════════════════════════╧════════════════╛""" in result.output
    assert not result.stderr
