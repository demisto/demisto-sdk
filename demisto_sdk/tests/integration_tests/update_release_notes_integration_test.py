import logging
from os.path import join
from pathlib import Path

import pytest
from click.testing import CliRunner

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.git_util import GitUtil
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.update_release_notes.update_rn import UpdateRN
from demisto_sdk.commands.update_release_notes.update_rn_manager import (
    UpdateReleaseNotesManager,
)
from demisto_sdk.commands.validate.old_validate_manager import OldValidateManager
from TestSuite.test_tools import ChangeCWD, str_in_call_args_list

UPDATE_RN_COMMAND = "update-release-notes"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")
TEST_FILES_PATH = join(git_path(), "demisto_sdk", "tests")
AZURE_FEED_PACK_PATH = join(
    TEST_FILES_PATH, "test_files", "content_repo_example", "Packs", "FeedAzureValid"
)
RN_FOLDER = join(git_path(), "Packs", "FeedAzureValid", "ReleaseNotes")
VMWARE_PACK_PATH = join(
    TEST_FILES_PATH, "test_files", "content_repo_example", "Packs", "VMware"
)
VMWARE_RN_PACK_PATH = join(git_path(), "Packs", "VMware", "ReleaseNotes")
THINKCANARY_RN_FOLDER = join(git_path(), "Packs", "ThinkCanary", "ReleaseNotes")

json = JSON_Handler()


@pytest.fixture
def demisto_client(mocker):
    mocker.patch(
        "demisto_sdk.commands.download.downloader.demisto_client",
        return_valure="object",
    )


def test_update_release_notes_new_integration(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    expected_rn = (
        "\n"
        + "#### Integrations\n\n"
        + "##### New: Azure Feed\n\n"
        + "- New: Azure.CloudIPs Feed Integration. (Available from Cortex XSOAR 5.5.0).\n"
    )
    added_files = {
        join(
            AZURE_FEED_PACK_PATH, "Integrations", "FeedAzureValid", "FeedAzureValid.yml"
        )
    }
    rn_path = join(RN_FOLDER, "1_0_1.md")
    runner = CliRunner(mix_stderr=True)
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_name",
        return_value="FeedAzureValid",
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(set(), added_files, set()),
    )
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")

    Path(rn_path).unlink(missing_ok=True)
    result = runner.invoke(
        main, [UPDATE_RN_COMMAND, "-i", join("Packs", "FeedAzureValid")]
    )
    assert result.exit_code == 0
    assert Path(rn_path).is_file()
    assert not result.exception
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping FeedAzureValid to version: 1.0.1",
                "Finished updating release notes for FeedAzureValid.",
            ]
        ]
    )

    with open(rn_path) as f:
        rn = f.read()
    assert expected_rn == rn


def test_update_release_notes_modified_integration(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    expected_rn = (
        "\n" + "#### Integrations\n\n" + "##### Azure Feed\n\n" + "- %%UPDATE_RN%%\n"
    )

    modified_files = {
        join(
            AZURE_FEED_PACK_PATH, "Integrations", "FeedAzureValid", "FeedAzureValid.yml"
        )
    }
    rn_path = join(RN_FOLDER, "1_0_1.md")

    runner = CliRunner(mix_stderr=False)
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
        return_value="",
    )
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(modified_files, set(), set()),
    )
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")

    Path(rn_path).unlink(missing_ok=True)

    result = runner.invoke(
        main, [UPDATE_RN_COMMAND, "-i", join("Packs", "FeedAzureValid")]
    )

    assert result.exit_code == 0
    assert Path(rn_path).is_file()
    assert not result.exception
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping FeedAzureValid to version: 1.0.1",
                "Finished updating release notes for FeedAzureValid.",
            ]
        ]
    )

    with open(rn_path) as f:
        rn = f.read()

    assert expected_rn == rn


def test_update_release_notes_incident_field(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    expected_rn = "\n" + "#### Incident Fields\n\n" + "- **City**\n"

    runner = CliRunner(mix_stderr=False)
    modified_files = {
        join(AZURE_FEED_PACK_PATH, "IncidentFields", "incidentfield-city.json")
    }
    rn_path = join(RN_FOLDER, "1_0_1.md")
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(modified_files, set(), set()),
    )
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")

    Path(rn_path).unlink(missing_ok=True)

    result = runner.invoke(
        main, [UPDATE_RN_COMMAND, "-i", join("Packs", "FeedAzureValid")]
    )

    assert result.exit_code == 0
    assert Path(rn_path).is_file()
    assert not result.exception
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping FeedAzureValid to version: 1.0.1",
                "Finished updating release notes for FeedAzureValid.",
            ]
        ]
    )

    with open(rn_path) as f:
        rn = f.read()
    assert expected_rn == rn


def test_update_release_notes_unified_yml_integration(demisto_client, mocker):
    """
    Given
    - VMware pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    expected_rn = (
        "\n" + "#### Integrations\n\n" + "##### VMware\n\n" + "- %%UPDATE_RN%%\n"
    )

    runner = CliRunner(mix_stderr=False)
    old_files = {join(VMWARE_PACK_PATH, "Integrations", "integration-VMware.yml")}
    rn_path = join(VMWARE_RN_PACK_PATH, "1_0_1.md")
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(set(), old_files, set()),
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="VMware"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")

    Path(rn_path).unlink(missing_ok=True)

    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-i", join("Packs", "VMware")])
    assert result.exit_code == 0
    assert not result.exception
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping VMware to version: 1.0.1",
                "Finished updating release notes for VMware.",
            ]
        ]
    )

    assert Path(rn_path).is_file()
    with open(rn_path) as f:
        rn = f.read()
    assert expected_rn == rn


def test_update_release_notes_non_content_path(demisto_client, mocker):
    """
    Given
    - non content pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure an error is raised
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    runner = CliRunner(mix_stderr=False)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        side_effect=FileNotFoundError,
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="VMware"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")

    result = runner.invoke(
        main, [UPDATE_RN_COMMAND, "-i", join("Users", "MyPacks", "VMware")]
    )

    assert result.exit_code == 1
    assert result.exception
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "You are not running",
    )


def test_update_release_notes_existing(demisto_client, mocker):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file updated with no errors
    - Ensure message is printed when update release notes process finished.
    - Ensure the release motes content is valid and as expected.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    expected_rn = (
        "\n"
        + "#### Integrations\n\n"
        + "##### New: Azure Feed\n\n"
        + "- Azure.CloudIPs Feed Integration.\n"
        + "\n"
        + "#### Incident Fields\n\n"
        + "- **City**\n\n"
    )

    input_rn = (
        "\n"
        + "#### Integrations\n\n"
        + "##### New: Azure Feed\n\n"
        + "- Azure.CloudIPs Feed Integration.\n"
    )

    rn_path = join(RN_FOLDER, "1_0_0.md")
    modified_files = {
        join(AZURE_FEED_PACK_PATH, "IncidentFields", "incidentfield-city.json")
    }
    with open(rn_path, "w") as file_:
        file_.write(input_rn)

    runner = CliRunner(mix_stderr=False)

    mocker.patch.object(UpdateRN, "is_bump_required", return_value=False)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(modified_files, set(), set()),
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
        return_value="",
    )
    result = runner.invoke(
        main, [UPDATE_RN_COMMAND, "-i", join("Packs", "FeedAzureValid")]
    )

    assert result.exit_code == 0
    assert Path(rn_path).exists()
    assert not result.exception
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "Finished updating release notes for FeedAzureValid.",
    )

    with open(rn_path) as f:
        rn = f.read()
    Path(rn_path).unlink()
    assert expected_rn == rn


def test_update_release_notes_modified_apimodule(demisto_client, repo, mocker):
    """
    Given
    - ApiModules_script.yml which is part of APIModules pack was changed.
    - FeedTAXII pack path exists and uses ApiModules_script

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors for APIModule and related pack FeedTAXII.
    - Ensure message is printed when update release notes process finished.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    # Set up packs and paths
    repo.setup_one_pack("ApiModules")
    api_module_pack = repo.packs[0]
    api_module_script_path = join(
        api_module_pack.path, "Scripts/ApiModules_script/ApiModules_script.yml"
    )

    repo.setup_one_pack("FeedTAXII")
    taxii_feed_pack = repo.packs[1]
    taxii_feed_integration = taxii_feed_pack.integrations[0]
    taxii_feed_integration.pack_id = "FeedTAXII"

    # Mock the behavior of Neo4jContentGraphInterface
    class MockedContentGraphInterface:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def search(self, object_id, all_level_imports):
            # Simulate the graph search
            if "ApiModules_script" in object_id:
                return [MockedApiModuleNode(id_) for id_ in object_id]
            return []

    class MockedApiModuleNode:
        def __init__(self, object_id):
            self.object_id = object_id
            self.imported_by = [
                MockedDependencyNode().integration
            ]  # Simulate a list of dependencies

    class MockedDependencyNode:
        integration = taxii_feed_integration

    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.ContentGraphInterface",
        return_value=MockedContentGraphInterface(),
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.update_content_graph",
    )
    modified_files = {api_module_script_path}
    runner = CliRunner(mix_stderr=False)

    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(modified_files, set(), set()),
    )
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
        return_value="",
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")

    result = runner.invoke(
        main,
        [UPDATE_RN_COMMAND, "-i", join("Packs", "ApiModules")],
    )

    assert result.exit_code == 0
    assert not result.exception
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Release notes are not required for the ApiModules pack since this pack is not versioned.",
                "Changes were detected. Bumping FeedTAXII to version: 1.0.1",
            ]
        ]
    )


def test_update_release_on_matadata_change(demisto_client, mocker, repo):
    """
    Given
    - change only in metadata (in fields that don't require RN)

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure not find changes which would belong in release notes .
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    pack = repo.create_pack("FeedAzureValid")
    pack.pack_metadata.write_json(
        open("demisto_sdk/tests/test_files/1.pack_metadata.json").read()
    )
    validate_manager = OldValidateManager(
        skip_pack_rn_validation=True,
        silence_init_prints=True,
        skip_conf_json=True,
        check_is_unskipped=False,
    )
    validate_manager.git_util = "Not None"

    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=({pack.pack_metadata.path}, set(), set()),
    )
    mocker.patch.object(
        UpdateReleaseNotesManager,
        "setup_validate_manager",
        return_value=validate_manager,
    )
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")

    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_names_from_files",
        return_value={"FeedAzureValid"},
    )
    mocker.patch.object(
        validate_manager,
        "get_changed_meta_files_that_should_have_version_raised",
        return_value=set(),
    )

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, [UPDATE_RN_COMMAND, "-g"])
    assert result.exit_code == 0
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "No changes that require release notes were detected. If such changes were made, "
                "please commit the changes and rerun the command",
            ]
        ]
    )


def test_update_release_notes_master_ahead_of_current(demisto_client, mocker, repo):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure the new version is taken from master and not from local metadata file.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    modified_files = {
        join(AZURE_FEED_PACK_PATH, "IncidentFields", "incidentfield-city.json")
    }
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        UpdateReleaseNotesManager,
        "get_git_changed_files",
        return_value=(modified_files, {"1_1_0.md"}, set()),
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="2.0.0")

    path_cwd = Path.cwd()
    mocker.patch.object(Path, "cwd", return_value=path_cwd)

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            main, [UPDATE_RN_COMMAND, "-i", join("Packs", "FeedAzureValid")]
        )
    assert result.exit_code == 0
    assert not result.exception

    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping FeedAzureValid to version: 2.0.1",
                "Finished updating release notes for FeedAzureValid.",
            ]
        ]
    )


def test_update_release_notes_master_unavailable(demisto_client, mocker, repo):
    """
    Given
    - Azure feed pack path.

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    - Ensure the new version is taken from local metadata file.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    modified_files = {
        join(
            AZURE_FEED_PACK_PATH, "Integrations", "FeedAzureValid", "FeedAzureValid.yml"
        )
    }
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        UpdateReleaseNotesManager,
        "get_git_changed_files",
        return_value=(modified_files, {"1_1_0.md"}, set()),
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.1.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
        return_value="",
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")

    path_cwd = Path.cwd()
    mocker.patch.object(Path, "cwd", return_value=path_cwd)

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(
            main, [UPDATE_RN_COMMAND, "-i", join("Packs", "FeedAzureValid")]
        )
    assert result.exit_code == 0
    assert not result.exception
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping FeedAzureValid to version: 1.1.1",
                "Finished updating release notes for FeedAzureValid.",
            ]
        ]
    )


def test_force_update_release_no_pack_given(demisto_client, repo, mocker):
    """
    Given
    - Nothing have changed.

    When
    - Running demisto-sdk update-release-notes command with --force flag but no specific pack is given.

    Then
    - Ensure that an error is printed.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    runner = CliRunner(mix_stderr=True)
    runner.invoke(main, [UPDATE_RN_COMMAND, "--force"])
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "Please add a specific pack in order to force",
    )


def test_update_release_notes_specific_version_invalid(demisto_client, repo):
    """
    Given
    - Nothing have changed.

    When
    - Running demisto-sdk update-release-notes command with --version flag but not in the right format.

    Then
    - Ensure that an error is printed.
    """
    runner = CliRunner(mix_stderr=True)
    result = runner.invoke(
        main, [UPDATE_RN_COMMAND, "-i", join("Packs", "ThinkCanary"), "-v", "3.x.t"]
    )
    assert (
        "The format of version should be in x.y.z format, e.g: <2.1.3>" in result.stdout
    )


def test_update_release_notes_specific_version_valid(demisto_client, mocker, repo):
    """
    Given
    - Azure feed pack path has changed.

    When
    - Running demisto-sdk update-release-notes command with --version flag.

    Then
    - Ensure release notes file created with no errors
    - Ensure the new version is taken from local metadata file.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    modified_files = {
        join(
            AZURE_FEED_PACK_PATH, "Integrations", "FeedAzureValid", "FeedAzureValid.yml"
        )
    }
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        UpdateReleaseNotesManager,
        "get_git_changed_files",
        return_value=(modified_files, {"1_1_0.md"}, set()),
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.1.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.common.tools.get_pack_name", return_value="FeedAzureValid"
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn.get_deprecated_rn",
        return_value="",
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="0.0.0")

    path_cwd = Path.cwd()
    mocker.patch.object(Path, "cwd", return_value=path_cwd)

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=True)
        result = runner.invoke(
            main,
            [UPDATE_RN_COMMAND, "-i", join("Packs", "FeedAzureValid"), "-v", "4.0.0"],
        )
    assert result.exit_code == 0
    assert not result.exception
    for current_call in logger_info.call_args_list:
        if type(current_call[0]) == tuple:
            print(f"*** INFO *** {current_call[0][0]=}")  # noqa: T201
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping FeedAzureValid to version: 4.0.0",
                "Finished updating release notes for FeedAzureValid.",
            ]
        ]
    )


def test_force_update_release(demisto_client, mocker, repo):
    """
    Given
    - Nothing have changed.

    When
    - Running demisto-sdk update-release-notes command with --force flag.

    Then
    - Ensure that RN were updated.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    rn_path = join(THINKCANARY_RN_FOLDER, "1_0_1.md")
    Path(rn_path).unlink(missing_ok=True)
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=(set(), set(), set()),
    )
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")
    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_name",
        return_value="ThinkCanary",
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_names_from_files",
        return_value={"ThinkCanary"},
    )

    runner = CliRunner(mix_stderr=True)
    runner.invoke(
        main, [UPDATE_RN_COMMAND, "-i", join("Packs", "ThinkCanary"), "--force"]
    )
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Bumping ThinkCanary to version: 1.0.1",
                "Finished updating release notes for ThinkCanary.",
            ]
        ]
    )

    with open(rn_path) as f:
        rn = f.read()
    assert "## ThinkCanary\n\n- %%UPDATE_RN%%\n" == rn


def test_update_release_notes_only_pack_ignore_changed(mocker, pack):
    """
    Given
    - only .pack-ignore file that was changed within a pack

    When
    - Running demisto-sdk update-release-notes command with -i flag

    Then
    - Ensure no release-notes need to be updated
    """
    mocker.patch.object(
        UpdateReleaseNotesManager,
        "get_git_changed_files",
        return_value=({pack.pack_ignore.path}, set(), set()),
    )
    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(
        UpdateRN,
        "bump_version_number",
        return_value=("1.2.3", {"currentVersion": "1.2.3"}),
    )

    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    runner = CliRunner(mix_stderr=True)
    result = runner.invoke(main, [UPDATE_RN_COMMAND, "-g"])
    assert result.exit_code == 0
    assert not result.exception
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "No changes that require release notes were detected. If such changes were made, please commit the changes and rerun the command",
    )


def test_update_release_on_matadata_change_that_require_rn(
    demisto_client, mocker, repo
):
    """
    Given
    - change only in metadata (in fields that require RN - dependencies)

    When
    - Running demisto-sdk update-release-notes command.

    Then
    - Ensure release notes file created with no errors
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    pack_metadata_path = "demisto_sdk/tests/test_files/1.pack_metadata.json"
    pack = repo.create_pack("FeedAzureValid")
    with open(pack_metadata_path) as metadata_file:
        metadata_file = json.load(metadata_file)
        pack.pack_metadata.write_json(metadata_file)
        old_pack_metadata = metadata_file.copy()
        old_pack_metadata["dependencies"] = {}

    validate_manager = OldValidateManager(
        skip_pack_rn_validation=True,
        silence_init_prints=True,
        skip_conf_json=True,
        check_is_unskipped=False,
    )

    mocker.patch.object(UpdateRN, "is_bump_required", return_value=True)
    mocker.patch.object(
        OldValidateManager,
        "get_unfiltered_changed_files_from_git",
        return_value=({pack.pack_metadata.path}, set(), set()),
    )
    mocker.patch.object(
        UpdateReleaseNotesManager,
        "setup_validate_manager",
        return_value=validate_manager,
    )
    mocker.patch.object(OldValidateManager, "setup_git_params", return_value="")

    mocker.patch.object(
        GitUtil, "get_current_working_branch", return_value="branch_name"
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_name",
        return_value="FeedAzureValid",
    )
    mocker.patch(
        "demisto_sdk.commands.update_release_notes.update_rn_manager.get_pack_names_from_files",
        return_value={"FeedAzureValid"},
    )
    mocker.patch(
        "demisto_sdk.commands.validate.old_validate_manager.get_remote_file",
        return_value=old_pack_metadata,
    )
    mocker.patch.object(
        UpdateRN, "get_pack_metadata", return_value={"currentVersion": "1.0.0"}
    )
    mocker.patch.object(UpdateRN, "get_master_version", return_value="1.0.0")
    rn_path = "Packs/FeedAzureValid/ReleaseNotes/1_0_1.md"

    Path(rn_path).unlink(missing_ok=True)
    path_cwd = Path.cwd()
    mocker.patch.object(Path, "cwd", return_value=path_cwd)

    with ChangeCWD(repo.path):
        runner = CliRunner(mix_stderr=True)
        result = runner.invoke(main, [UPDATE_RN_COMMAND, "-g"])

    assert result.exit_code == 0
    assert not result.exception
    assert all(
        [
            str_in_call_args_list(logger_info.call_args_list, current_str)
            for current_str in [
                "Changes were detected. Bumping FeedAzureValid to version: 1.0.1",
                "Finished updating release notes for FeedAzureValid.",
            ]
        ]
    )

    assert Path(rn_path).is_file()
