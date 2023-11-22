import logging
from io import BytesIO
from os.path import join
from pathlib import Path
from zipfile import ZipFile

import demisto_client
import pytest
from click.testing import CliRunner
from packaging.version import Version

from demisto_sdk.__main__ import main
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import YAML_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack_metadata import PackMetadata
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.parsers.pack import PackParser
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
    import demisto_sdk.commands.content_graph.objects.content_item as content_item

    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
    pack_path = Path(
        DEMISTO_SDK_PATH, "tests/test_files/content_repo_example/Packs/FeedAzure"
    )
    mocker.patch.object(
        content_item,
        "CONTENT_PATH",
        Path(DEMISTO_SDK_PATH, "tests/test_files/content_repo_example"),
    )

    for content_class in (
        IncidentField,
        Integration,
        Playbook,
        Script,
    ):
        mock_upload_method(mocker, content_class)

    runner = CliRunner(mix_stderr=False)
    mocker.patch.object(PackParser, "parse_ignored_errors", return_value={})
    result = runner.invoke(
        main, [UPLOAD_CMD, "-i", str(pack_path), "--insecure", "--no-zip"]
    )
    assert result.exit_code == 0
    logged = flatten_call_args(logger_info.call_args)
    assert len(logged) == 1
    assert logged[0] == "\n".join(
        (
            "[green]SUCCESSFUL UPLOADS:",
            "╒═════════════════════════╤═══════════════╤═══════════════╤════════════════╕",
            "│ NAME                    │ TYPE          │ PACK NAME     │ PACK VERSION   │",
            "╞═════════════════════════╪═══════════════╪═══════════════╪════════════════╡",
            "│ incidentfield-city.json │ IncidentField │ AzureSentinel │ 1.0.0          │",
            "├─────────────────────────┼───────────────┼───────────────┼────────────────┤",
            "│ FeedAzure.yml           │ Integration   │ AzureSentinel │ 1.0.0          │",
            "├─────────────────────────┼───────────────┼───────────────┼────────────────┤",
            "│ FeedAzure_test.yml      │ Playbook      │ AzureSentinel │ 1.0.0          │",
            "╘═════════════════════════╧═══════════════╧═══════════════╧════════════════╛",
            "[/green]",
        )
    )


METADATA_DISPLAYS = {
    "automation": "Automation",
    "classifier": "Classifiers",
    "dashboard": "Dashboard",
    "genericdefinition": "Generic Definition",
    "genericfield": "Generic Field",
    "genericmodule": "Generic Module",
    "generictype": "Generic Type",
    "incidentfield": "Incident Field",
    "incidenttype": "Incident Type",
    "indicatorfield": "Indicator Field",
    "integration": "Integration",
    "job": "Jobs",
    "layoutscontainer": "Layouts Container",
    "list": "List",
    "playbook": "Playbooks",
    "report": "Report",
    "reputation": "Reputation",
    "widget": "Widget",
}

METADATA_NAMES = [
    "automation",
    "classifier",
    "dashboard",
    "genericdefinition",
    "genericfield",
    "genericmodule",
    "generictype",
    "incidentfield",
    "incidenttype",
    "indicatorfield",
    "integration",
    "job",
    "layoutscontainer",
    "list",
    "playbook",
    "report",
    "reputation",
    "widget",
]


def test_zipped_pack_upload_positive(repo, mocker, tmpdir, demisto_client_mock):
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
    mocker.patch.object(PackMetadata, "_get_tags_from_landing_page", retrun_value={})
    mocker.patch.object(Path, "cwd", return_value=Path.cwd())

    pack = repo.setup_one_pack(name="test-pack")
    runner = CliRunner(mix_stderr=False)
    with ChangeCWD(pack.repo_path):
        result = runner.invoke(
            main,
            [UPLOAD_CMD, "-i", pack.path, "-z", "--insecure", "--keep-zip", tmpdir],
        )
        assert result.exit_code == SUCCESS_RETURN_CODE

    with ZipFile(f"{tmpdir}/uploadable_packs.zip") as result_zip:
        with ZipFile(BytesIO(result_zip.read("test-pack.zip"))) as pack_zip:
            assert set(pack_zip.namelist()) == {
                "Author_image.png",
                "Classifiers/",
                "Classifiers/classifier-mapper-test-pack_mapper.json",
                "Classifiers/classifier-test-pack_classifier.json",
                "Dashboards/",
                "Dashboards/dashboard-test-pack_dashboard.json",
                "GenericDefinitions/",
                "GenericDefinitions/genericdefinition-test-pack_generic-definition.json",
                "GenericFields/",
                "GenericFields/test-pack_generic-field/",
                "GenericFields/test-pack_generic-field/genericfield-test-pack_generic-field.json",
                "GenericModules/",
                "GenericModules/genericmodule-test-pack_generic-module.json",
                "GenericTypes/",
                "GenericTypes/test-pack_generic-type/",
                "GenericTypes/test-pack_generic-type/generictype-test-pack_generic-type.json",
                "IncidentFields/",
                "IncidentFields/incidentfield-test-pack_incident-field.json",
                "IncidentTypes/",
                "IncidentTypes/incidenttype-test-pack_incident-type.json",
                "IndicatorFields/",
                "IndicatorFields/incidentfield-indicatorfield-test-pack_indicator-field.json",
                "IndicatorTypes/",
                "IndicatorTypes/reputation-test-pack_indicator-type.json",
                "Integrations/",
                "Integrations/integration-test-pack_integration.yml",
                "Jobs/",
                "Jobs/job-test-pack.json",
                "Jobs/job-test-pack_all_feeds.json",
                "Layouts/",
                "Layouts/layoutscontainer-test-pack_layoutcontainer.json",
                "Lists/",
                "Lists/list-test-pack_list.json",
                "Playbooks/",
                "Playbooks/playbook-test-pack_all_feeds_playbook.yml",
                "Playbooks/playbook-test-pack_playbook.yml",
                "README.md",
                "ReleaseNotes/",
                "Reports/",
                "Reports/report-test-pack_report.json",
                "Scripts/",
                "Scripts/script-test-pack_script.yml",
                "Widgets/",
                "Widgets/widget-test-pack_widget.json",
                "Wizards/",
                "Wizards/wizard-test-pack_wizard.json",
                "metadata.json",
                "pack_metadata.json",
            }

            with pack_zip.open(
                "Layouts/layoutscontainer-test-pack_layoutcontainer.json"
            ) as layout:
                # validate json based content entities are being unified before getting zipped
                assert {"fromServerVersion", "toServerVersion"}.issubset(
                    json.load(layout).keys()
                )

            with pack_zip.open(
                "Integrations/integration-test-pack_integration.yml"
            ) as integration:
                # validate yml based content entities are being unified before getting zipped
                assert "nativeimage" in yaml.load(integration).get("script", {})

            with pack_zip.open("metadata.json") as metadata:
                metadata = json.load(metadata)
                assert "contentDisplays" in metadata
                metadata_display = metadata.get("contentDisplays")
                for content_item in METADATA_NAMES:
                    assert (
                        metadata_display[content_item]
                        == METADATA_DISPLAYS[content_item]
                    )

    logged = flatten_call_args(logger_info.call_args_list)
    assert mocked_get_installed.called_once_with(
        "/contentpacks/metadata/installed", "GET"
    )
    assert logged[-1] == "\n".join(
        (
            "[green]SUCCESSFUL UPLOADS:",
            "╒═══════════╤════════╤═════════════╤════════════════╕",
            "│ NAME      │ TYPE   │ PACK NAME   │ PACK VERSION   │",
            "╞═══════════╪════════╪═════════════╪════════════════╡",
            "│ test-pack │ Pack   │ test-pack   │ 1.0.0          │",
            "╘═══════════╧════════╧═════════════╧════════════════╛",
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
        "demisto_sdk.commands.upload.uploader.get_demisto_version",
        return_value=Version("0"),
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(main, [UPLOAD_CMD, "-i", pack_path, "--insecure"])
    assert result.exit_code == 1
    assert str_in_call_args_list(
        logger_info.call_args_list,
        "Could not connect to the server. Try checking your connection configurations.",
    )


def test_upload_single_list(mocker, pack):
    """
    Given
    - Content pack with list content item.

    When
    - Uploading the list content item.

    Then
    - Ensure the list is uploaded successfully.
    """
    from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

    with (Path(DEMISTO_SDK_PATH) / "tests/test_files/list-valid.json").open(
        "r"
    ) as _list_content:
        _list_data = pack.create_list(
            name="test-valid-list-upload", content=json.load(_list_content)
        )

    mocker.patch(
        "demisto_sdk.commands.upload.uploader.demisto_client", return_valure="object"
    )
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.get_demisto_version",
        return_value=Version("6.8.0"),
    )
    mocker.patch.object(ContentItem, "pack_name", return_value="PackWithList")
    mocker.patch.object(ContentItem, "pack_version", return_value="1.2.0")

    runner = CliRunner(mix_stderr=False)

    with ChangeCWD(pack.repo_path):
        result = runner.invoke(
            main,
            [UPLOAD_CMD, "-i", _list_data.path],
        )
    assert result.exit_code == SUCCESS_RETURN_CODE


def test_upload_single_indicator_field(mocker, pack):
    """
    Given
    - Content pack with an indicator field.

    When
    - Uploading the indicator field.

    Then
    - Ensure the indicator field is uploaded successfully.
    """
    from demisto_sdk.commands.common.constants import GENERAL_DEFAULT_FROMVERSION
    from demisto_sdk.commands.content_graph.objects.content_item import ContentItem

    indicator_field = pack.create_indicator_field(
        "test-upload",
        content={
            "id": "indicator_testupload",
            "version": -1,
            "name": "test",
            "cliName": "test",
            "type": "markdown",
            "description": "test",
            "associatedToAll": False,
            "fromVersion": "5.5.0",
        },
    )

    logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

    mocker.patch(
        "demisto_sdk.commands.upload.uploader.demisto_client", return_valure="object"
    )
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.get_demisto_version",
        return_value=Version(GENERAL_DEFAULT_FROMVERSION),
    )

    mocker.patch.object(ContentItem, "pack_name", return_value="PackWithIndicatorField")
    mocker.patch.object(ContentItem, "pack_version", return_value="1.2.0")

    runner = CliRunner(mix_stderr=False)

    with ChangeCWD(pack.repo_path):
        result = runner.invoke(
            main,
            [UPLOAD_CMD, "-i", indicator_field.path],
        )
    assert result.exit_code == SUCCESS_RETURN_CODE
    assert str_in_call_args_list(logger_info.call_args_list, "SUCCESSFUL UPLOADS")
