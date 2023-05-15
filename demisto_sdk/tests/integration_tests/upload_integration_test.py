import logging
import shutil
import tempfile
from os.path import join
from pathlib import Path

import demisto_client
import pytest
from click.testing import CliRunner
from packaging.version import Version

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.handlers import JSON_Handler, YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.upload.tests.uploader_test import (
    API_CLIENT,
    mock_upload_method,
)
from demisto_sdk.commands.upload.uploader import (
    ERROR_RETURN_CODE,
    SUCCESS_RETURN_CODE,
)
from TestSuite.test_tools import ChangeCWD, flatten_call_args, str_in_call_args_list

UPLOAD_CMD = "upload"
DEMISTO_SDK_PATH = join(git_path(), "demisto_sdk")


json = JSON_Handler()
yaml = YAML_Handler()


@pytest.fixture
def demisto_client_mock(mocker):
    mocker.patch.object(demisto_client, "configure", return_value=API_CLIENT)

    mocker.patch(
        "demisto_sdk.commands.upload.uploader.get_demisto_version",
        return_value=Version("6.8.0"),
    )


def test_integration_upload_pack_positive(demisto_client_mock, mocker):
    """
    Given
    - Content pack named FeedAzure to upload.

    When
    - Uploading the pack.

    Then
    - Ensure upload runs successfully.
    - Ensure success upload message is printed.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    pack_path = Path(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure"
    )
    for content_class in (
        IncidentField,
        Integration,
        Playbook,
        Script,
    ):
        mock_upload_method(mocker, content_class)

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", str(pack_path), "--insecure"])
    assert result.exit_code == 0

    assert all(
        str_in_call_args_list(logger_info.call_args_list, current_str)
        for current_str in [
            "SUCCESSFUL UPLOADS:",
            "│ NAME                                       │ TYPE          │",
            "│ incidentfield-city.json                    │ IncidentField │",
            "│ FeedAzure.yml                              │ Integration   │",
            "│ FeedAzure_test.yml                         │ Playbook      │",
            "│ just_a_test_script.yml                     │ Script        │",
            "│ script-prefixed_automation.yml             │ Script        │",
            "│ playbook-FeedAzure_test_copy_no_prefix.yml │ TestPlaybook  │",
            "│ FeedAzure_test.yml                         │ TestPlaybook  │",
        ]
    )


def test_zipped_pack_upload_positive(repo, mocker, demisto_client_mock):
    """
    Given
    - content pack name

    When
    - Uploading the zipped pack.

    Then
    - Ensure upload runs successfully.
    - Ensure success upload message is printed.
    - ensure yml / json content items inside the pack are getting unified.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    mocker.patch.object(
        API_CLIENT, "upload_content_packs", return_value=({}, 200, None)
    )
    mocked_get_installed = mocker.patch.object(
        API_CLIENT, "generic_request", return_value=({}, 200, None)
    )

    pack = repo.setup_one_pack(name="test-pack")
    runner = CliRunner(mix_stderr=False)
    with tempfile.TemporaryDirectory() as dir:
        with ChangeCWD(pack.repo_path):
            result = runner.invoke(
                main,
                [UPLOAD_CMD, "-i", pack.path, "-z", "--insecure", "--keep-zip", dir],
            )
            assert result.exit_code == SUCCESS_RETURN_CODE
        shutil.unpack_archive(f"{dir}/uploadable_packs.zip", dir, "zip")
        shutil.unpack_archive(f"{dir}/test-pack.zip", dir, "zip")

        with open(
            f"{dir}/Layouts/layoutscontainer-test-pack_layoutcontainer.json"
        ) as file:
            layout_content = json.load(file)

        # validate json based content entities are being unified before getting zipped
        assert {"fromServerVersion", "toServerVersion"}.issubset(layout_content.keys())

        with open(f"{dir}/Integrations/integration-test-pack_integration.yml") as file:
            integration_content = yaml.load(file)

        # validate yml based content entities are being unified before getting zipped
        assert "nativeimage" in integration_content.get("script", {})

    logged = flatten_call_args(logger_info.call_args_list)
    assert mocked_get_installed.called_once_with(
        "/contentpacks/metadata/installed", "GET"
    )
    assert logged[-1] == "\n".join(
        (
            "[green]SUCCESSFUL UPLOADS:",
            "╒═══════════╤════════╕",
            "│ NAME      │ TYPE   │",
            "╞═══════════╪════════╡",
            "│ test-pack │ Pack   │",
            "╘═══════════╧════════╛",
            "[/green]",
        )
    )


def test_integration_upload_path_does_not_exist(demisto_client_mock):
    """
    Given
    - Directory path which does not exist.

    When
    - Uploading the directory.

    Then
    - Ensure upload fails.
    - Ensure failure upload message is printed to the stderr as the failure caused by click.Path.convert check.
    """
    invalid_dir_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/DoesNotExist"
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", invalid_dir_path, "--insecure"])
    assert result.exit_code == 2
    assert isinstance(result.exception, SystemExit)
    assert (
        f"Invalid value for '-i' / '--input': Path '{invalid_dir_path}' does not exist"
        in result.stderr
    )


def test_integration_upload_script_invalid_path(demisto_client_mock, tmp_path, mocker):
    """
    Given
    - Directory with invalid path - "Script" instead of "Scripts".

    When
    - Uploading the script.

    Then
    - Ensure upload fails due to invalid path.
    - Ensure failure upload message is printed.
    """
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    path = tmp_path / "Script" / "InvalidScript"
    path.mkdir(parents=True)
    runner = CliRunner(mix_stderr=False)

    result = runner.invoke(main, [UPLOAD_CMD, "-i", str(path), "--insecure"])
    logged_errors = flatten_call_args(logger_error.call_args_list)

    assert result.exit_code == ERROR_RETURN_CODE
    assert str(path) in logged_errors[0]
    assert "Nothing to upload: the" in logged_errors[1]


def test_integration_upload_pack_invalid_connection_params(mocker):
    """
    Given
    - Content pack with "invalid" connection params.

    When
    - Uploading the pack.

    Then
    - Ensure pack is not uploaded and correct error message is printed.
    """
    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    pack_path = join(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure"
    )
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.demisto_client", return_valure="object"
    )
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.get_demisto_version", return_value="0"
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", pack_path, "--insecure"])
    assert result.exit_code == 1
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "Could not connect to XSOAR server. Try checking your connection configurations.",
    )
