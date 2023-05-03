import inspect
import logging
import re
import shutil
import zipfile
from functools import wraps
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from unittest.mock import MagicMock, patch

import click
import demisto_client
import pytest
from click.testing import CliRunner
from demisto_client.demisto_api import DefaultApi
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version

from demisto_sdk.__main__ import main, upload
from demisto_sdk.commands.common.constants import (
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.content_graph.objects.layout import Layout
from demisto_sdk.commands.content_graph.objects.mapper import Mapper
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.widget import Widget
from demisto_sdk.commands.test_content import tools
from demisto_sdk.commands.upload import uploader
from demisto_sdk.commands.upload.uploader import (
    ERROR_RETURN_CODE,
    SUCCESS_RETURN_CODE,
    ItemDetacher,
    Uploader,
    parse_error_response,
)
from TestSuite.test_tools import flatten_call_args, str_in_call_args_list

json = JSON_Handler()


def mock_upload_method(mocker: Any, class_: ContentItem):
    return mocker.patch.object(
        class_,
        "_client_upload_method",
        return_value=lambda path: ({}, 200, "Headers"),
    )


DATA = ""
DUMMY_SCRIPT_OBJECT: ContentItem = BaseContent.from_path(  # type:ignore[assignment]
    Path(
        f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/DummyScript/DummyScript.py"
    )
)
# Taken from https://github.com/pytest-dev/pytest-bdd/issues/155
if not hasattr(inspect, "_orig_findsource"):

    @wraps(inspect.findsource)
    def findsource(*args, **kwargs):
        try:
            return inspect._orig_findsource(*args, **kwargs)
        except IndexError:
            raise OSError("Invalid line")

    inspect._orig_findsource = inspect.findsource
    inspect.findsource = findsource


@pytest.fixture
def demisto_client_configure(mocker):
    mocker.patch(
        "demisto_sdk.commands.upload.uploader.get_demisto_version",
        return_value=Version("6.0.0"),
    )
    mocker.patch(
        "demisto_sdk.commands.common.content.objects.pack_objects.integration.integration.get_demisto_version",
        return_value=Version("6.0.0"),
    )
    mocker.patch(
        "demisto_sdk.commands.common.content.objects.pack_objects.script.script.get_demisto_version",
        return_value=Version("6.0.0"),
    )
    mocker.patch("builtins.print")


@pytest.mark.parametrize(
    "path_end,item_count",
    (
        ("content_repo_example/Integrations/Securonix/", 1),
        ("content_repo_example/Integrations", 1),
        ("Packs/DummyPack/Scripts", 1),
        ("Packs/DummyPack/Scripts/DummyScript", 1),
        ("Packs/DummyPack/IncidentFields", 3),
    ),
)
def test_upload_folder(
    demisto_client_configure, mocker, path_end: str, item_count: int
):
    """
    Given
            A path to a content item folder
    When
            Instantiating an uploader with this path, and calling upload
    Then
            Make sure the expected count of content items have their _upload method called
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    mock_upload = mocker.patch.object(
        ContentItem,
        "_upload",
    )
    path = Path(f"{git_path()}/demisto_sdk/tests/test_files/", path_end)
    assert path.exists()
    uploader = Uploader(path)
    with patch.object(uploader, "client", return_value="ok"):
        assert (
            uploader.upload() == SUCCESS_RETURN_CODE
        ), f"failed uploading {'/'.join(path.parts[-2:])}"
    assert len(uploader._successfully_uploaded_content_items) == item_count
    assert mock_upload.call_count == item_count


@pytest.mark.parametrize(
    "content_class,path",
    [
        (
            Integration,
            "demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/Securonix.yml",
        ),
        (
            Integration,
            "demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/Securonix.py",
        ),
        (
            Script,
            "demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/DummyScriptUnified.yml",
        ),
        (
            Playbook,
            "demisto_sdk/tests/test_files/Packs/CortexXDR/Playbooks/Cortex_XDR_Incident_Handling.yml",
        ),
        (
            Widget,
            "demisto_sdk/tests/test_files/Packs/DummyPack/Widgets/widget-ActiveIncidentsByRole.json",
        ),
        (
            Dashboard,
            "demisto_sdk/tests/test_files/Packs/DummyPack/Dashboards/upload_test_dashboard.json",
        ),
        (
            Layout,
            "demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/layoutscontainer-test.json",
        ),
        (
            IncidentType,
            "demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/incidenttype-Hello_World_Alert.json",
        ),
        (
            Mapper,
            "demisto_sdk/tests/test_files/Packs/DummyPack/Classifiers/classifier-aws_sns_test_classifier.json",
        ),
        (
            IncidentField,
            "demisto_sdk/tests/test_files/Packs/CortexXDR/IncidentFields/XDR_Alert_Count.json",
        ),
        (
            IndicatorField,
            "demisto_sdk/tests/test_files/Packs/CortexXDR/IndicatorFields/dns.json",
        ),
        (
            IndicatorType,
            "demisto_sdk/tests/test_files/Packs/CortexXDR/IndicatorTypes/SampleIndicatorType.json",
        ),
    ],
)
def test_upload_single_positive(mocker, path: str, content_class: ContentItem):
    """
    Given
        - A path to a content item

    When
        - Uploading the content item

    Then
        - Ensure its _client_upload_method is called once
    """
    # prepare
    mock_api_client(mocker)

    assert content_class._client_upload_method is not None
    mocked_client_upload_method = mock_upload_method(mocker, content_class)

    path = Path(git_path(), path)
    assert path.exists()
    assert BaseContent.from_path(path) is not None, f"Failed parsing {path.absolute()}"

    uploader = Uploader(input=path)
    mocker.patch.object(uploader, "client")

    # run
    uploader.upload()

    assert len(uploader._successfully_uploaded_content_items) == 1
    assert mocked_client_upload_method.called_once()


def test_upload_single_not_supported(mocker):
    """
    Given
            An Uploader
    When
            Attempting to upload a layout of an old format
    Then
            Make sure an appropriate error is shown
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    mock_api_client(mocker)

    path = Path(
        git_path(),
        "demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/layout-details-test_bla-V2.json",
    )
    assert path.exists()
    assert BaseContent.from_path(path) is None
    uploader = Uploader(input=path)

    uploader.upload()

    assert len(uploader.failed_parsing) == 1
    failed_path, reason = uploader.failed_parsing[0]
    assert failed_path == path
    assert reason == "Deprecated type - use LayoutContainer instead"


def test_upload_incident_type_correct_file_change(demisto_client_configure, mocker):
    """
    Given
        - An incident type named incidenttype-Hello_World_Alert to upload

    When
        - Uploading incident type

    Then
        - Ensure incident type is in the correct format for upload
    """

    def save_file(file):
        global DATA
        DATA = Path(file).read_text()
        return ({}, 200, "")

    class ConfigurationMock:
        host = "host"

    class demisto_client_mocker:
        class ConfigurationMock:
            host = "host"

        class ApiClientMock:
            configuration = ConfigurationMock()

        api_client = ApiClientMock()

        def import_incident_fields(self, file):
            pass

    mocker.patch.object(demisto_client, "configure", return_value=demisto_client_mocker)

    path = Path(
        f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/incidenttype-Hello_World_Alert.json"
    )
    uploader = Uploader(input=path, insecure=False)
    uploader.client.import_incident_types_handler = MagicMock(side_effect=save_file)
    uploader.upload()

    with open(path) as json_file:
        incident_type_data = json.load(json_file)

    assert json.loads(DATA)[0] == incident_type_data


def test_upload_incident_field_correct_file_change(demisto_client_configure, mocker):
    """
    Given
        - An incident field named XDR_Alert_Count to upload

    When
        - Uploading incident field

    Then
        - Ensure incident field is in the correct format for upload
    """

    def save_file(file):
        global DATA
        DATA = Path(file).read_text()
        return ({}, 200, "")

    class ConfigurationMock:
        host = "host"

    class demisto_client_mocker:
        class ConfigurationMock:
            host = "host"

        class ApiClientMock:
            configuration = ConfigurationMock()

        api_client = ApiClientMock()

        def import_incident_fields(self, file):
            pass

    mocker.patch.object(demisto_client, "configure", return_value=demisto_client_mocker)
    path = Path(
        f"{git_path()}/demisto_sdk/tests/test_files/Packs/CortexXDR/IncidentFields/XDR_Alert_Count.json"
    )
    uploader = Uploader(input=path, insecure=False)
    uploader.client.import_incident_fields = MagicMock(
        side_effect=save_file,
    )
    assert uploader.upload() == SUCCESS_RETURN_CODE

    with open(path) as json_file:
        incident_field_data = json.load(json_file)

    assert json.loads(DATA)[0]["incidentFields"] == incident_field_data


def test_upload_pack(demisto_client_configure, mocker):
    """
    Given
        - A pack called DummyPack

    When
        - Uploading pack

    Then
        - Ensure pack is uploaded successfully
        - Ensure status code is as expected
        - Check that all expected content entities that appear in the pack are reported as uploaded.
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    mocker.patch.object(
        IntegrationScript, "get_supported_native_images", return_value=[]
    )
    path = Path(f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack")
    uploader = Uploader(path)
    mocker.patch.object(uploader, "client")
    mocked_upload_method = mocker.patch.object(ContentItem, "upload")
    expected_entities = [
        "DummyIntegration.yml",
        "UploadTest.yml",
        "DummyScriptUnified.yml",
        "DummyScript.yml",
        "DummyPlaybook.yml",
        "DummyTestPlaybook.yml",
        "incidenttype-Hello_World_Alert.json",
        "incidentfield-Hello_World_ID.json",
        "incidentfield-Hello_World_Type.json",
        "incidentfield-Hello_World_Status.json",
        "classifier-aws_sns_test_classifier.json",
        "widget-ActiveIncidentsByRole.json",
        "layoutscontainer-test.json",
        "upload_test_dashboard.json",
        "DummyXDRCTemplate.json",
    ]
    assert uploader.upload() == SUCCESS_RETURN_CODE
    assert {
        content_item.path.name
        for content_item in uploader._successfully_uploaded_content_items
    } == set(expected_entities)
    assert mocked_upload_method.call_count == len(expected_entities)


def test_upload_invalid_path(mocker):
    logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
    mocker.patch.object(demisto_client, "configure", return_value="object")

    path = Path(
        f"{git_path()}/demisto_sdk/tests/test_files/content_repo_not_exists/Scripts/"
    )
    uploader = Uploader(input=path, insecure=False)
    assert uploader.upload() == ERROR_RETURN_CODE
    assert not any(
        (
            uploader.failed_parsing,
            uploader._failed_upload_content_items,
            uploader._failed_upload_version_mismatch,
        )
    )
    assert flatten_call_args(logger_error.call_args_list) == (
        f"[red]input path: {path.resolve()} does not exist[/red]",
    )


def test_upload_single_unsupported_file(mocker):
    """
    Given
        - A not supported (.json) file

    When
        - Uploading a file

    Then
        - Ensure uploaded failure message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    path = Path(
        f"{git_path()}/demisto_sdk/tests/test_files/fake_pack/Integrations/test_data/results.json"
    )
    uploader = Uploader(input=path)
    mocker.patch.object(uploader, "client")
    assert uploader.upload() == ERROR_RETURN_CODE
    assert uploader.failed_parsing == [(path, "unknown")]


@pytest.mark.parametrize(
    "exc,expected_message",
    [
        (
            ApiException(reason="[SSL: CERTIFICATE_VERIFY_FAILED]"),
            "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\nRun the command with the --insecure flag.",
        ),
        (
            ApiException(reason="Failed to establish a new connection:"),
            "Failed to establish a new connection: Connection refused.\n"
            "Check the BASE url configuration.",
        ),
    ],
)
def test_parse_error_response(exc: ApiException, expected_message: str):
    """
    Given
        - An API exception is raised

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify the outcome is as expected
    """
    assert parse_error_response(exc) == expected_message


@pytest.mark.parametrize("reason", ("Bad Request", "Forbidden"))
def test_parse_error_response__exception(reason: str):
    """
    Given
        - An API exception is raised

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify the outcome is as expected
    """
    api_exception = ApiException(reason=reason)
    api_exception.body = json.dumps({"status": 403, "error": "Error message"})
    assert (
        parse_error_response(api_exception)
        == "Error message\nTry checking your API key configuration."
    )


class TestPrintSummary:
    def test_print_summary_successfully_uploaded_files(
        self,
        demisto_client_configure,
        mocker,
    ):
        """
        Given
            - An uploader object with one successfully-uploaded object

        When
            - Printing summary of uploaded files

        Then
            - Ensure uploaded successfully message is printed as expected
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        mock_api_client(mocker)

        uploader = Uploader(None)
        uploader._successfully_uploaded_content_items = [DUMMY_SCRIPT_OBJECT]
        uploader.print_summary()

        logged = flatten_call_args(logger_info.call_args_list)
        assert len(logged) == 2

        assert logged[0] == "UPLOAD SUMMARY:\n"
        assert logged[1] == "\n".join(
            (
                "[green]SUCCESSFUL UPLOADS:",
                "╒═════════════════╤════════╕",
                "│ NAME            │ TYPE   │",
                "╞═════════════════╪════════╡",
                "│ DummyScript.yml │ Script │",
                "╘═════════════════╧════════╛",
                "[/green]",
            )
        )

    def test_print_summary_failed_uploaded(self, demisto_client_configure, mocker):
        """
        Given
            - A uploaded script named SomeScriptName which failed to upload

        When
            - Printing summary of uploaded files

        Then
            - Ensure uploaded failure message is printed as expected
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        mock_api_client(mocker)

        uploader = Uploader(None)
        uploader._failed_upload_content_items = [(DUMMY_SCRIPT_OBJECT, "Some Error")]
        uploader.print_summary()

        assert logger_info.call_count == 2
        logged = flatten_call_args(logger_info.call_args_list)

        assert logged[0] == "UPLOAD SUMMARY:\n"
        assert logged[1] == "\n".join(
            (
                "[red]FAILED UPLOADS:",
                "╒═════════════════╤════════╤════════════╕",
                "│ NAME            │ TYPE   │ ERROR      │",
                "╞═════════════════╪════════╪════════════╡",
                "│ DummyScript.yml │ Script │ Some Error │",
                "╘═════════════════╧════════╧════════════╛",
                "[/red]",
            )
        )

    def test_print_summary_version_mismatch(
        self, demisto_client_configure, mocker, repo
    ):
        """
        Given
            - A uploaded script named SomeScriptName which did not upload due to version mismatch

        When
            - Printing summary of uploaded files

        Then
            - Ensure uploaded unuploaded message is printed as expected
        """
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        mock_api_client(mocker)

        pack = repo.create_pack()
        script = pack.create_script()
        script.yml.update({"fromversion": "0.0.0", "toversion": "1.2.3"})
        path = Path(script.path)

        uploader = Uploader(path)
        assert uploader.demisto_version == Version("6.6.0")
        assert uploader.upload() == ERROR_RETURN_CODE
        assert uploader._failed_upload_version_mismatch == [BaseContent.from_path(path)]

        logged = flatten_call_args(logger_info.call_args_list)
        assert len(logged) == 3
        assert logged[0] == (
            f"Uploading {path.absolute()} to {uploader.client.api_client.configuration.host}..."
        )
        assert logged[1] == "UPLOAD SUMMARY:\n"
        assert logged[2] == (
            "\n".join(
                (
                    "[yellow]NOT UPLOADED DUE TO VERSION MISMATCH:",
                    "╒═════════════╤════════╤═════════════════╤═════════════════════╤═══════════════════╕",
                    "│ NAME        │ TYPE   │ XSOAR Version   │ FILE_FROM_VERSION   │ FILE_TO_VERSION   │",
                    "╞═════════════╪════════╪═════════════════╪═════════════════════╪═══════════════════╡",
                    "│ script0.yml │ Script │ 6.6.0           │ 0.0.0               │ 1.2.3             │",
                    "╘═════════════╧════════╧═════════════════╧═════════════════════╧═══════════════════╛",
                    "[/yellow]",
                )
            )
        )


TEST_DATA = src_root() / "commands" / "upload" / "tests" / "data"
CONTENT_PACKS_ZIP = TEST_DATA / "content_packs.zip"
TEST_PACK_ZIP = TEST_DATA / "TestPack.zip"
TEST_PACK = "Packs/TestPack"
TEST_XSIAM_PACK = "Packs/TestXSIAMPack"
API_CLIENT = DefaultApi()


def mock_api_client(mocker, version: str = "6.6.0"):
    mocker.patch.object(demisto_client, "configure", return_value=API_CLIENT)
    mocker.patch.object(uploader, "get_demisto_version", return_value=Version(version))


class TestZippedPackUpload:
    @pytest.mark.parametrize("path", (TEST_PACK_ZIP, CONTENT_PACKS_ZIP))
    def test_upload_zipped_packs(self, mocker, path: Path):
        """
        Given:
            - zipped pack or zip of pack zips to upload
        When:
            - call to upload command
        Then:
            - validate the upload_content_packs in the api client was called correct
              and the pack verification ws turned on and off
        """
        # prepare
        mock_api_client(mocker)
        mocked_upload_content_packs = mocker.patch.object(
            API_CLIENT, "upload_content_packs", return_value=({}, 200, "")
        )
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True  # TODO
        )

        # run
        uploader = Uploader(path)
        assert uploader.upload() == SUCCESS_RETURN_CODE

        # validate
        assert len(uploader._successfully_uploaded_zipped_packs) == 1
        assert mocked_upload_content_packs.call_args[1]["file"] == str(path)

    @pytest.mark.parametrize(
        argnames="path", argvalues=(Path("invalid_zip_path"), None)
    )
    def test_upload_invalid_zip_path(self, mocker, path: Optional[Path]):
        """
        Given:
            - invalid path in the input argument
        When:
            - run the upload zipped pack
        Then:
            - validate the error msg
        """
        # prepare
        logger_error = mocker.patch.object(logging.getLogger("demisto-sdk"), "error")
        mock_api_client(mocker)

        # run
        status = click.Context(command=upload).invoke(upload, input=path)

        # validate
        assert status == ERROR_RETURN_CODE

        logged = flatten_call_args(logger_error.call_args_list)
        assert len(logged) == 1
        assert f"input path: {path} does not exist" in logged[0]

    @pytest.mark.parametrize(
        argnames="user_answer, exp_call_count", argvalues=[("y", 1), ("n", 0)]
    )
    def test_notify_user_about_overwrite_pack(
        self, mocker, user_answer, exp_call_count
    ):
        """
        Given:
            - Zip of pack to upload where this pack already installed
        Where:
            - Upload this pack
        Then:
            - Validate user asked if sure to overwrite this pack
        """
        mock_api_client(mocker)
        mocker.patch("builtins.input", return_value=user_answer)
        mocker.patch.object(
            tools, "update_server_configuration", return_value=(None, None, {})
        )
        mocker.patch.object(
            API_CLIENT,
            "generic_request",
            return_value=[json.dumps([{"name": "TestPack"}])],
        )
        mocker.patch.object(API_CLIENT, "upload_content_packs")

        # run
        click.Context(command=upload).invoke(upload, input=TEST_PACK_ZIP)

        # validate
        tools.update_server_configuration.call_count == exp_call_count

    def test_upload_zip_does_not_exist(self):
        """
        Given:
            - Zip path which does not exist.

        When:
            - Uploading the zipped pack.

        Then:
            - Ensure upload fails.
            - Ensure failure upload message is printed to the stderr as the failure caused by click.Path.convert check.
        """
        invalid_zip_path = "not_exist_dir/not_exist_zip"
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(main, ["upload", "-i", invalid_zip_path, "--insecure"])
        assert result.exit_code == 2
        assert isinstance(result.exception, SystemExit)
        assert (
            f"Invalid value for '-i' / '--input': Path '{invalid_zip_path}' does not exist"
            in result.stderr
        )

    @pytest.mark.parametrize(
        argnames="path", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    @pytest.mark.parametrize("version", ("6.5.0", "6.6.0", "6.10.0"))
    def test_upload_with_skip_verify(self, mocker, path: Path, version: str):
        """
        Given:
            - zipped pack or zip of pack zips to upload
        When:
            - call to upload command with client >=6.5.0
        Then:
            - validate the upload_content_packs in the api client was called correct
              and the skip_verify arg is "true"
        """
        # prepare
        mock_api_client(mocker, version)
        # mocker.patch.object( # TODO
        #     Uploader, "notify_user_should_override_packs", return_value=True
        # )
        mock_upload_content_packs = mocker.patch.object(
            API_CLIENT, "upload_content_packs", return_value=({}, 200, None)
        )
        # run
        click.Context(command=upload).invoke(upload, input=path)
        assert mock_upload_content_packs.call_count == 1
        assert mock_upload_content_packs.call_args[1]["file"] == str(path)
        assert mock_upload_content_packs.call_args[1]["skip_verify"] == "true"

    @pytest.mark.parametrize(
        argnames="path", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    @pytest.mark.parametrize("version", ("6.6.0", "6.10.0"))
    def test_upload_with_skip_validation(self, mocker, path: Path, version: str):
        """
        Given:
            - zipped pack or zip of pack zips to upload
            - demisto version >=6.5.0
        When:
            - call to upload command with skip_validation=True
        Then:
            - validate the upload_content_packs in the api client was called correctly
              and the skip_validate arg is "true"
        """
        # prepare
        mock_api_client(mocker, version)

        mocker.patch.object(
            tools, "update_server_configuration", return_value=(None, None, {})
        )
        mock_upload_content_packs = mocker.patch.object(
            API_CLIENT, "upload_content_packs", return_value=({}, 200, None)
        )
        # mocker.patch.object( # TODO
        #     Uploader, "notify_user_should_override_packs", return_value=True
        # )

        # run
        result = click.Context(command=upload).invoke(
            upload, input=path, skip_validation=True
        )

        assert result == SUCCESS_RETURN_CODE

        upload_call_args = mock_upload_content_packs.call_args[1]
        assert upload_call_args["skip_validation"] == "true"
        assert upload_call_args["file"] == str(path)

    @pytest.mark.parametrize(
        argnames="path", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    @pytest.mark.parametrize("version", ("6.5.0", "6.6.0", "6.10.0"))
    def test_upload_without_skip_validate(self, mocker, path: Path, version: str):
        """
        Given:
            - zipped pack or zip of pack zips to upload
        When:
            - call to upload command
        Then:
            - validate the upload_content_packs in the api client was called correct
              and the skip_validate arg is None
        """
        # prepare
        mock_api_client(mocker, version)
        mock_upload_content_packs = mocker.patch.object(
            API_CLIENT, "upload_content_packs", return_value=({}, 200, None)
        )

        mocker.patch.object(
            tools, "update_server_configuration", return_value=(None, None, {})
        )
        # mocker.patch.object( # TODO
        #     Uploader, "notify_user_should_override_packs", return_value=True
        # )

        # run
        click.Context(command=upload).invoke(upload, input=path)
        assert mock_upload_content_packs.call_args[1]["file"] == str(path)
        assert mock_upload_content_packs.call_args[1].get("skip_validate") is None

    # def test_upload_xsiam_pack_to_xsiam(self, mocker):
    #     """
    #     Given:
    #         - XSIAM pack to upload to XSIAM
    #     When:
    #         - call to upload command
    #     Then:
    #         - Make sure XSIAM entities are in the zip we want to upload
    #     """
    #     # prepare
    #     mock_api_client(mocker)
    #     mocker.patch.object(Uploader, 'zipped_pack_uploader')
    #
    #     # run
    #     click.Context(command=upload).invoke(upload, input=TEST_XSIAM_PACK, xsiam=True, zip=True)
    #
    #     zip_file_path = Uploader.zipped_pack_uploader.call_args[1]['path']
    #
    #     assert 'uploadable_packs.zip' in zip_file_path
    #
    #     with zipfile.ZipFile(zip_file_path, "r") as zfile:
    #         for name in zfile.namelist():
    #             if re.search(r'\.zip$', name) is not None:
    #                 # We have a zip within a zip
    #                 zfiledata = BytesIO(zfile.read(name))
    #                 with zipfile.ZipFile(zfiledata) as xsiamzipfile:
    #                     xsiam_pack_files = xsiamzipfile.namelist()
    #
    #     assert 'Triggers/' in xsiam_pack_files
    #     assert 'XSIAMDashboards/' in xsiam_pack_files
    @pytest.mark.parametrize(argnames="is_cleanup", argvalues=(True, False))
    def test_upload_xsiam_pack_to_xsoar(self, mocker, is_cleanup: bool):
        """
        Given:
            - XSIAM pack to upload to XSOAR
        When:
            - call to upload command
        Then:
            - Make sure XSIAM entities are not in the zip we want to upload
        """
        if not is_cleanup:
            mocker.patch.object(shutil, "rmtree")
        mock_api_client(mocker)
        mocked_upload_content_packs = mocker.patch.object(
            API_CLIENT, "upload_content_packs", return_value=({}, 200, None)
        )

        click.Context(command=upload).invoke(
            upload,
            input=TEST_XSIAM_PACK,
            xsiam=False,
            zip=True,
        )
        zip_path = Path(mocked_upload_content_packs.call_args.kwargs["file"])
        assert zip_path.exists() != is_cleanup

        if is_cleanup:
            return  # the following code only checks the other case

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            for file_name in filter(
                lambda _file_name: re.search(r"\.zip$", _file_name) is not None,
                zip_file.namelist(),
            ):
                xsiam_pack_files = zipfile.ZipFile(
                    BytesIO(zip_file.read(file_name))
                ).namelist()
                break
        assert len(xsiam_pack_files) == 2

        # XSIAM entities are not supposed to be uploaded to XSOAR
        assert "Triggers/" not in xsiam_pack_files
        assert "XSIAMDashboards/" not in xsiam_pack_files


class TestItemDetacher:
    def test_detach_item(self, mocker):
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")

        mock_api_client(mocker)
        mocker.patch.object(
            API_CLIENT,
            "generic_request",
            return_value=[json.dumps([{"name": "TestPack"}])],
        )

        ItemDetacher.detach_item(
            ItemDetacher(API_CLIENT, marketplace=MarketplaceVersions.XSOAR),
            file_id="file",
            file_path="Scripts/file_path",
        )

        assert logger_info.call_count == 1
        assert str_in_call_args_list(
            logger_info.call_args_list,
            "File: file was detached",
        )

    def test_extract_items_from_dir(self, mocker, repo):
        repo = repo.setup_one_pack(name="Pack")
        list_items = ItemDetacher(
            client=API_CLIENT,
            file_path=repo.path,
            marketplace=MarketplaceVersions.XSOAR,
        ).extract_items_from_dir()
        assert len(list_items) == 8
        for item in list_items:
            assert (
                "Playbooks" in item.get("file_path")
                or "Layouts" in item.get("file_path")
                or "IncidentTypes" in item.get("file_path")
                or "IncidentTypes" in item.get("file_path")
            )

    @pytest.mark.parametrize(
        argnames="file_path, res",
        argvalues=[
            ("Packs/Pack/Playbooks/Process_Survey_Response.yml", True),
            ("Packs/Pack/Playbooks/Process_Survey_Response.md", False),
            ("Packs/Pack/Scripts/Process_Survey_Response.yml", True),
            ("Packs/Pack/Scripts/Process_Survey_Response.md", False),
        ],
    )
    def test_is_valid_file_for_detach(self, file_path, res):
        assert (
            ItemDetacher(
                client=API_CLIENT, marketplace=MarketplaceVersions.XSOAR
            ).is_valid_file_for_detach(file_path=file_path)
            == res
        )

    @pytest.mark.parametrize(
        argnames="file_path, res",
        argvalues=[
            ("Packs/Pack/Playbooks/Process_Survey_Response.yml", "yml"),
            ("Packs/Pack/Playbooks/Process_Survey_Response.md", "yml"),
            ("Packs/Pack/IncidentTypes/Process_Survey_Response.json", "json"),
            ("Packs/Pack/Layouts/Process_Survey_Response.json", "json"),
        ],
    )
    def test_find_item_type_to_detach(self, file_path, res):
        assert (
            ItemDetacher(
                client=API_CLIENT, marketplace=MarketplaceVersions.XSOAR
            ).find_item_type_to_detach(file_path=file_path)
            == res
        )

    def test_find_item_id_to_detach(self, repo):
        pack = repo.create_pack("Pack1")
        playbook1 = pack.create_playbook("MyPlay1")
        playbook1.create_default_playbook()
        assert (
            ItemDetacher(
                client=API_CLIENT,
                file_path=f"{playbook1.path}/MyPlay1.yml",
                marketplace=MarketplaceVersions.XSOAR,
            ).find_item_id_to_detach()
            == "sample playbook"
        )

    def test_detach_item_manager(self, mocker, repo):
        mock_api_client(mocker)
        mocker.patch.object(
            API_CLIENT,
            "generic_request",
            return_value=[json.dumps([{"name": "TestPack"}])],
        )

        repo = repo.setup_one_pack(name="Pack")
        detached_items_ids = ItemDetacher(
            client=API_CLIENT,
            file_path=repo.path,
            marketplace=MarketplaceVersions.XSOAR,
        ).detach()
        assert len(detached_items_ids) == 8
        for file_id in detached_items_ids:
            assert file_id in [
                "Pack_playbook",
                "job-Pack_playbook",
                "job-Pack_all_feeds_playbook",
                "Pack_integration_test_playbook",
                "Pack_script_test_playbook",
                "Pack - layoutcontainer",
                "Pack - layout",
                "Pack - incident_type",
            ]

        detached_items_ids = ItemDetacher(
            client=API_CLIENT,
            file_path=f"{repo._pack_path}/Playbooks/Pack_playbook.yml",
            marketplace=MarketplaceVersions.XSOAR,
        ).detach()
        assert len(detached_items_ids) == 1
        assert detached_items_ids == ["Pack_playbook"]


def exception_raiser(**kwargs):
    raise Exception()
