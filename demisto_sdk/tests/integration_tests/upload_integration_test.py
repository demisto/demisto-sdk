from io import BytesIO
from os.path import join
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from zipfile import ZipFile

import demisto_client
import pytest
from packaging.version import Version
from rich.console import Console
from typer.testing import CliRunner

from demisto_sdk.__main__ import app
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
    SUCCESS_RETURN_CODE,
)
from TestSuite.test_tools import ChangeCWD

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
        app, [UPLOAD_CMD, "-i", str(pack_path), "--insecure", "--no-zip"]
    )
    assert result.exit_code == 0
    assert (
        "\n".join(
            (
                "SUCCESSFUL UPLOADS:",
                "╒═════════════════════════╤═══════════════╤═══════════════╤════════════════╕",
                "│ NAME                    │ TYPE          │ PACK NAME     │ PACK VERSION   │",
                "╞═════════════════════════╪═══════════════╪═══════════════╪════════════════╡",
                "│ incidentfield-city.json │ IncidentField │ AzureSentinel │ 1.0.0          │",
                "├─────────────────────────┼───────────────┼───────────────┼────────────────┤",
                "│ FeedAzure.yml           │ Integration   │ AzureSentinel │ 1.0.0          │",
                "├─────────────────────────┼───────────────┼───────────────┼────────────────┤",
                "│ FeedAzure_test.yml      │ Playbook      │ AzureSentinel │ 1.0.0          │",
                "╘═════════════════════════╧═══════════════╧═══════════════╧════════════════╛",
            )
        )
        in result.output
    )


def test_integration_upload_pack_with_specific_marketplace(demisto_client_mock, mocker):
    """
    Given
    - Content pack named Example Pack to upload.

    When
    - Uploading the pack.

    Then
    - Ensure upload runs successfully.
    - Ensure success upload message is printed.
    - Ensure Skipped message is printed.
    """
    import demisto_sdk.commands.content_graph.objects.content_item as content_item

    pack_path = Path(
        DEMISTO_SDK_PATH,
        "tests/test_files/content_repo_example/Packs/ExamplePack/Integrations",
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
        app, [UPLOAD_CMD, "-i", str(pack_path), "--insecure", "--marketplace", "xsoar"]
    )
    assert result.exit_code == 0
    assert "SKIPPED UPLOADING DUE TO MARKETPLACE MISMATCH:" in result.output
    assert "Upload Destination Marketplace" in result.output
    assert "Content Marketplace(s)" in result.output
    assert (
        "integration-sample_event_collector.yml │ Integration │ xsoar                            │ marketplacev2"
        in result.output
    )
    assert "Did you forget to specify the marketplace?" in result.output

    assert (
        "\n".join(
            (
                "SUCCESSFUL UPLOADS:",
                "╒══════════════════════════════╤═════════════╤═════════════╤════════════════╕",
                "│ NAME                         │ TYPE        │ PACK NAME   │ PACK VERSION   │",
                "╞══════════════════════════════╪═════════════╪═════════════╪════════════════╡",
                "│ integration-sample_packs.yml │ Integration │ ExamplePack │ 3.0.0          │",
                "╘══════════════════════════════╧═════════════╧═════════════╧════════════════╛",
            )
        )
        in result.output
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


def test_zipped_pack_upload_positive(
    repo, mocker, tmpdir, demisto_client_mock, monkeypatch
):
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

    mocker.patch.object(
        API_CLIENT, "upload_content_packs", return_value=({}, 200, None)
    )
    mocker.patch.object(API_CLIENT, "generic_request", return_value=({}, 200, None))
    mocker.patch.object(PackMetadata, "_get_tags_from_landing_page", retrun_value={})
    mocker.patch.object(Path, "cwd", return_value=Path.cwd())

    pack = repo.setup_one_pack(name="test-pack")
    runner = CliRunner(mix_stderr=False)
    with ChangeCWD(pack.repo_path):
        with TemporaryDirectory() as artifact_dir:
            monkeypatch.setenv("DEMISTO_SDK_CONTENT_PATH", artifact_dir)
            monkeypatch.setenv("ARTIFACTS_FOLDER", artifact_dir)
            result = runner.invoke(
                app,
                [
                    UPLOAD_CMD,
                    "-i",
                    str(pack.path),
                    "-z",
                    "--insecure",
                    "--keep-zip",
                    tmpdir,
                ],
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
                "version_config.json",
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

    assert (
        "\n".join(
            (
                "SUCCESSFUL UPLOADS:",
                "╒═══════════╤════════╤═════════════╤════════════════╕",
                "│ NAME      │ TYPE   │ PACK NAME   │ PACK VERSION   │",
                "╞═══════════╪════════╪═════════════╪════════════════╡",
                "│ test-pack │ Pack   │ test-pack   │ 1.0.0          │",
                "╘═══════════╧════════╧═════════════╧════════════════╛",
            )
        )
        in result.output
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

    # Mock rich Console to avoid rich formatting during tests
    with mock.patch.object(Console, "print", wraps=Console().print) as mock_print:
        runner = CliRunner(mix_stderr=True)
        result = runner.invoke(app, [UPLOAD_CMD, "-i", invalid_dir_path, "--insecure"])

        assert result.exit_code == 2
        assert isinstance(result.exception, SystemExit)

        # Check for error message in the output
        assert "Invalid value for '--input' / '-i'" in result.stdout
        assert "does not exist" in result.stdout
        mock_print.assert_called()


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
        "demisto_sdk.commands.upload.uploader.demisto_client", return_valure="object"
    )
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.get_demisto_version",
        return_value=Version("0"),
    )
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(app, [UPLOAD_CMD, "-i", pack_path, "--insecure"])
    assert result.exit_code == 1
    assert (
        "Could not connect to the server. Try checking your connection configurations."
        in result.output
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
            app,
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
            app,
            [UPLOAD_CMD, "-i", indicator_field.path],
        )
    assert result.exit_code == SUCCESS_RETURN_CODE
    assert "SUCCESSFUL UPLOADS" in result.output
