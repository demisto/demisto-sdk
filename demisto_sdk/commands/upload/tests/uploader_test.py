import inspect
import logging
import re
import shutil
import tempfile
import zipfile
from functools import wraps
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import click
import demisto_client
import pytest
from click.testing import CliRunner
from demisto_client.demisto_api import DefaultApi
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version

from demisto_sdk.__main__ import main, upload
from demisto_sdk.commands.common import constants
from demisto_sdk.commands.common.constants import (
    DELETE_VERIFY_KEY_ACTION_FORMAT,
    TURN_VERIFICATION_ERROR_MSG_FORMAT,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
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


DATA = ""
DUMMY_SCRIPT_OBJECT: ContentItem = BaseContent.from_path(
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
    mocker.patch.object(demisto_client, "configure", return_value="object")
    path = Path(f"{git_path()}/demisto_sdk/tests/test_files/", path_end)
    assert path.exists()
    uploader = Uploader(path)
    with patch.object(uploader, "client", return_value="ok"):
        assert (
            uploader.upload() == SUCCESS_RETURN_CODE
        ), f"failed uploading {'/'.join(path.parts[-2:])}"
    assert len(uploader.successfully_uploaded) == item_count


@pytest.mark.parametrize(
    "test_name,path",
    [
        (
            "integration-yml",
            "demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/Securonix.yml",
        ),
        (
            "integration-py",
            "demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/Securonix.py",
        ),
        (
            "script-yml-unified",
            "demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/DummyScriptUnified.yml",
        ),
        (
            "playbook",
            "demisto_sdk/tests/test_files/Packs/CortexXDR/Playbooks/Cortex_XDR_Incident_Handling.yml",
        ),
        (
            "widget",
            "demisto_sdk/tests/test_files/Packs/DummyPack/Widgets/widget-ActiveIncidentsByRole.json",
        ),
        (
            "dashboard",
            "demisto_sdk/tests/test_files/Packs/DummyPack/Dashboards/upload_test_dashboard.json",
        ),
        (
            "layoutscontainer",
            "demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/layoutscontainer-test.json",
        ),
        (
            "incident-type",
            "demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/incidenttype-Hello_World_Alert.json",
        ),
        (
            "classifier-old",
            "demisto_sdk/tests/test_files/Packs/DummyPack/Classifiers/classifier-aws_sns_test_classifier.json",
        ),
        (
            "incident-field",
            "demisto_sdk/tests/test_files/Packs/CortexXDR/IncidentFields/XDR_Alert_Count.json",
        ),
        (
            "indicator-field",
            "demisto_sdk/tests/test_files/Packs/CortexXDR/IndicatorFields/dns.json",
        ),
        (
            "indicator-type",
            "demisto_sdk/tests/test_files/Packs/CortexXDR/IndicatorTypes/SampleIndicatorType.json",
        ),
    ],
)
def test_upload_single_positive(mocker, test_name: str, path: str):
    """
    Given
        - A path to a content item

    When
        - Uploading the content item

    Then
        - Ensure it is uploaded successfully
    """
    mock_api_client(mocker)
    path = Path(git_path(), path)
    assert path.exists()
    assert BaseContent.from_path(path) is not None, f"Failed parsing {path.absolute()}"
    uploader = Uploader(input=path)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert uploader.successfully_uploaded == [BaseContent.from_path(path)]


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
        with open(file) as f:
            DATA = f.read()
        return

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
        with open(file) as f:
            DATA = f.read()
        return

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
    uploader.client.import_incident_fields = MagicMock(side_effect=save_file)
    uploader.upload()

    with open(path) as json_file:
        incident_field_data = json.load(json_file)

    assert json.loads(DATA)["incidentFields"] == incident_field_data


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
        content_item.path.name for content_item in uploader.successfully_uploaded
    } == set(expected_entities)

    assert uploader.failed_parsing == [  # TODO
        (Path("layout-details-test_bla-V2.json", "foo"))
    ]


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
            uploader.failed_upload,
            uploader.failed_upload_version_mismatch,
        )
    )
    assert flatten_call_args(logger_error.call_args_list) == (
        f"[red]input path: {path.resolve()} does not exist[/red]",
    )


def test_upload_file_not_supported(mocker):
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
    assert uploader.failed_parsing == [(path, "")]


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
        uploader.successfully_uploaded = [DUMMY_SCRIPT_OBJECT]
        uploader.print_summary()

        logged = flatten_call_args(logger_info.call_args_list)
        assert len(logged) == 2

        assert "UPLOAD SUMMARY:\n" in logged
        assert (
            "\n".join(
                (
                    "[green]SUCCESSFUL UPLOADS:\n",
                    "╒═════════════════╤════════╕",
                    "│ NAME            │ TYPE   │",
                    "╞═════════════════╪════════╡",
                    "│ DummyScript.yml │ Script │",
                    "╘═════════════════╧════════╛[/green]",
                )
            )
            in logged
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
        uploader.failed_upload = [(DUMMY_SCRIPT_OBJECT, "Some Error")]
        uploader.print_summary()

        assert logger_info.call_count == 2
        logged = flatten_call_args(logger_info.call_args_list)

        assert "UPLOAD SUMMARY:\n" in logged
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
        assert uploader.demisto_version == Version("6.0.0")
        assert uploader.upload() == ERROR_RETURN_CODE
        assert uploader.failed_upload_version_mismatch == [BaseContent.from_path(path)]

        logged = flatten_call_args(logger_info.call_args_list)
        assert len(logged) == 3
        assert (
            f"Uploading {path.absolute()} to {uploader.client.api_client.configuration.host}..."
            in logged
        )
        assert "UPLOAD SUMMARY:\n" in logged
        assert (
            "\n".join(
                (
                    "[yellow]NOT UPLOADED DUE TO VERSION MISMATCH:",
                    "╒═════════════╤════════╤═════════════════╤═════════════════════╤═══════════════════╕",
                    "│ NAME        │ TYPE   │ XSOAR Version   │ FILE_FROM_VERSION   │ FILE_TO_VERSION   │",
                    "╞═════════════╪════════╪═════════════════╪═════════════════════╪═══════════════════╡",
                    "│ script0.yml │ Script │ 6.0.0           │ 0.0.0               │ 1.2.3             │",
                    "╘═════════════╧════════╧═════════════════╧═════════════════════╧═══════════════════╛[/yellow]",
                )
            )
            in logged
        )


TEST_DATA = src_root() / "commands" / "upload" / "tests" / "data"
CONTENT_PACKS_ZIP = str(TEST_DATA / "content_packs.zip")
TEST_PACK_ZIP = str(TEST_DATA / "TestPack.zip")
TEST_PACK = "Packs/TestPack"
TEST_XSIAM_PACK = "Packs/TestXSIAMPack"
INVALID_ZIP = "invalid_zip"
INVALID_ZIP_ERROR = "Error: Given input path: {path} does not exist"
API_CLIENT = DefaultApi()


def mock_api_client(mocker):
    mocker.patch.object(demisto_client, "configure", return_value=API_CLIENT)
    mocker.patch.object(uploader, "get_demisto_version", return_value=Version("6.0.0"))


class TestZippedPackUpload:
    """
    Happy path tests:
        1. Upload one zipped pack
        2. Upload content_artifacts.zip with multiple packs
        3. Upload with compile flag
        4. Server configs return to the previous value after upload

    Edge cases tests:
        1. Invalid zip path
        2. Error in disable pack verification
        3. Error in enable pack verification
        4. Error in upload to marketplace

    """

    @pytest.mark.parametrize(
        argnames="input", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    def test_upload_zipped_packs(self, mocker, input):
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
        mocker.patch.object(API_CLIENT, "upload_content_packs")
        mocker.patch.object(Pack, "is_server_version_ge", return_value=False)
        mocker.patch.object(
            tools, "update_server_configuration", return_value=(None, None, {})
        )
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )

        # run
        click.Context(command=upload).invoke(upload, input=input)

        # validate
        disable_verification_call_args = (
            tools.update_server_configuration.call_args_list[0][1]
        )
        enable_verification_call_args = (
            tools.update_server_configuration.call_args_list[1][1]
        )

        assert (
            disable_verification_call_args["server_configuration"][
                constants.PACK_VERIFY_KEY
            ]
            == "false"
        )
        assert (
            constants.PACK_VERIFY_KEY
            in enable_verification_call_args["config_keys_to_delete"]
        )
        uploaded_file_path = API_CLIENT.upload_content_packs.call_args[1]["file"]
        assert str(uploaded_file_path) == input

    def test_server_config_after_upload(self, mocker):
        """
        Given:
            - zipped pack to upload
        When:
            - call to update server configuration
        Then:
            - validate the origin configs are set to server configuration after upload
        """
        # prepare
        mock_api_client(mocker)
        mocker.patch.object(API_CLIENT, "upload_content_packs")
        mocker.patch.object(Pack, "is_server_version_ge", return_value=False)
        mocker.patch.object(
            tools,
            "update_server_configuration",
            return_value=(None, None, {constants.PACK_VERIFY_KEY: "prev_val"}),
        )
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )

        # run
        click.Context(command=upload).invoke(upload, input=TEST_PACK_ZIP)

        # validate
        disable_verification_call_args = (
            tools.update_server_configuration.call_args_list[0][1]
        )
        enable_verification_call_args = (
            tools.update_server_configuration.call_args_list[1][1]
        )

        assert (
            disable_verification_call_args["server_configuration"][
                constants.PACK_VERIFY_KEY
            ]
            == "false"
        )
        assert (
            enable_verification_call_args["server_configuration"][
                constants.PACK_VERIFY_KEY
            ]
            == "prev_val"
        )

    @pytest.mark.parametrize(
        argnames="input, expected_ret_value", argvalues=[(INVALID_ZIP, 1), (None, 1)]
    )
    def test_upload_invalid_zip_path(self, mocker, input, expected_ret_value):
        """
        Given:
            - invalid path in the input argument
        When:
            - run the upload zipped pack
        Then:
            - validate the error msg
        """
        # prepare
        logger_info = mocker.patch.object(logging.getLogger("demisto-sdk"), "info")
        mock_api_client(mocker)

        # run
        status = click.Context(command=upload).invoke(upload, input=input)

        # validate
        assert status == expected_ret_value
        assert str_in_call_args_list(
            logger_info.call_args_list, INVALID_ZIP_ERROR.format(path=input)
        )

    def test_error_in_disable_pack_verification(self, mocker):
        """
        Given:
            - error occurred when try to disable the pack verification
        When:
            - upload zipped pack
        Then:
            - validate the result status are 1 (error) and the upload_content_packs was not called
        """

        # prepare
        mock_api_client(mocker)
        mocker.patch.object(tools, "update_server_configuration", new=exception_raiser)
        mocker.patch.object(API_CLIENT, "upload_content_packs")

        # run
        status = click.Context(command=upload).invoke(upload, input=TEST_PACK_ZIP)

        # validate
        assert status == 1
        assert API_CLIENT.upload_content_packs.call_count == 0

    def test_error_in_enable_pack_verification(self, mocker):
        """
        Given:
            - error occurred when try to enable again the pack verification
        When:
            - run the upload for zipped pack
        Then:
            - validate DefaultApi.upload_content_packs was called (as the error occurred after that)
              and validate the detailed error message
        """

        # prepare
        def conditional_exception_raiser(**kwargs):
            # raise exception only when try to enable again the pack verification
            if kwargs.pop("config_keys_to_delete", None):
                raise Exception()
            return None, None, {}

        mock_api_client(mocker)
        mocker.patch.object(uploader, "parse_error_response")
        mocker.patch.object(Pack, "is_server_version_ge", return_value=False)
        mocker.patch.object(
            tools, "update_server_configuration", new=conditional_exception_raiser
        )
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )
        mocker.patch.object(API_CLIENT, "upload_content_packs")

        # run
        status = click.Context(command=upload).invoke(upload, input=TEST_PACK_ZIP)

        # validate
        assert status == 1
        assert API_CLIENT.upload_content_packs.call_count == 1
        exp_err_msg = TURN_VERIFICATION_ERROR_MSG_FORMAT.format(
            action=DELETE_VERIFY_KEY_ACTION_FORMAT
        )
        assert str(uploader.parse_error_response.call_args[0][0]) == exp_err_msg

    def test_error_in_upload_to_marketplace(self, mocker):
        """
        Given:
            - error occurred when try to upload the zip to marketplace
        When:
            - run the upload for zipped pack
        Then:
            - validate the status result are 1 (error) and the pack verification was enabled again
        """
        mock_api_client(mocker)
        mocker.patch.object(
            tools, "update_server_configuration", return_value=(None, None, {})
        )
        mocker.patch.object(Pack, "is_server_version_ge", return_value=False)
        mocker.patch.object(API_CLIENT, "upload_content_packs", new=exception_raiser)
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )

        # run
        status = click.Context(command=upload).invoke(upload, input=TEST_PACK_ZIP)

        # validate

        disable_verification_call_args = (
            tools.update_server_configuration.call_args_list[0][1]
        )
        enable_verification_call_args = (
            tools.update_server_configuration.call_args_list[1][1]
        )
        assert status == 1
        assert (
            disable_verification_call_args["server_configuration"][
                constants.PACK_VERIFY_KEY
            ]
            == "false"
        )
        assert (
            constants.PACK_VERIFY_KEY
            in enable_verification_call_args["config_keys_to_delete"]
        )

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

    def test_upload_custom_packs_from_config_file(self, mocker):
        """
        Given:
            - Configuration file with custom packs (zipped packs and unzipped packs) to upload
        When:
            - call to upload command
        Then:
            - validate the upload_content_packs in the api client was called correct
              and the pack verification ws turned on and off
              ans status code is 0 (Ok)
        """
        # prepare
        mock_api_client(mocker)
        mocker.patch.object(API_CLIENT, "upload_content_packs")
        mocker.patch.object(Pack, "is_server_version_ge", return_value=False)
        mocker.patch.object(
            tools, "update_server_configuration", return_value=(None, None, {})
        )
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )

        # run
        status_code = click.Context(command=upload).invoke(
            upload,
            input_config_file=f"{git_path()}/demisto_sdk/commands/upload/tests/data/xsoar_config.json",
        )

        # validate
        disable_verification_call_args = (
            tools.update_server_configuration.call_args_list[0][1]
        )
        enable_verification_call_args = (
            tools.update_server_configuration.call_args_list[1][1]
        )

        assert (
            disable_verification_call_args["server_configuration"][
                constants.PACK_VERIFY_KEY
            ]
            == "false"
        )
        assert (
            constants.PACK_VERIFY_KEY
            in enable_verification_call_args["config_keys_to_delete"]
        )
        assert status_code == 0

        uploaded_file_path = API_CLIENT.upload_content_packs.call_args[1]["file"]
        assert "uploadable_packs.zip" in str(uploaded_file_path)

    @pytest.mark.parametrize(
        argnames="input", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    def test_upload_with_skip_verify(self, mocker, input):
        """
        Given:
            - zipped pack or zip of pack zips to upload
        When:
            - call to upload command
        Then:
            - validate the upload_content_packs in the api client was called correct
              and the skip_verify arg is "true"
        """
        # prepare
        mock_api_client(mocker)
        mocker.patch.object(API_CLIENT, "upload_content_packs")
        mocker.patch.object(Pack, "is_server_version_ge", return_value=True)
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )

        # run
        click.Context(command=upload).invoke(upload, input=input)

        skip_value = API_CLIENT.upload_content_packs.call_args[1]["skip_verify"]
        uploaded_file_path = API_CLIENT.upload_content_packs.call_args[1]["file"]

        assert str(uploaded_file_path) == input
        assert skip_value == "true"

    @pytest.mark.parametrize(
        argnames="input", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    def test_upload_without_skip_verify(self, mocker, input):
        """
        Given:
            - zipped pack or zip of pack zips to upload
        When:
            - call to upload command
        Then:
            - validate the upload_content_packs in the api client was called correct
              and the skip_verify arg is None
        """
        # prepare
        mock_api_client(mocker)
        mocker.patch.object(API_CLIENT, "upload_content_packs")
        mocker.patch.object(
            tools, "update_server_configuration", return_value=(None, None, {})
        )
        mocker.patch.object(Pack, "is_server_version_ge", return_value=False)
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )

        # run
        click.Context(command=upload).invoke(upload, input=input)
        uploaded_file_path = API_CLIENT.upload_content_packs.call_args[1]["file"]

        assert str(uploaded_file_path) == input

        try:
            skip_value = API_CLIENT.upload_content_packs.call_args[1]["skip_verify"]
        except KeyError:
            skip_value = None
        assert not skip_value

    @pytest.mark.parametrize(
        argnames="input", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    def test_upload_with_skip_validation(self, mocker, input):
        """
        Given:
            - zipped pack or zip of pack zips to upload
        When:
            - call to upload command
        Then:
            - validate the upload_content_packs in the api client was called correct
              and the skip_validate arg is "true"
        """
        # prepare
        mock_api_client(mocker)
        mocker.patch.object(API_CLIENT, "upload_content_packs")
        mocker.patch.object(Pack, "is_server_version_ge", return_value=True)
        mocker.patch.object(
            Uploader, "notify_user_should_override_packs", return_value=True
        )

        # run
        click.Context(command=upload).invoke(upload, input=input, skip_validation=True)

        skip_value = API_CLIENT.upload_content_packs.call_args[1]["skip_validation"]
        uploaded_file_path = API_CLIENT.upload_content_packs.call_args[1]["file"]

        assert str(uploaded_file_path) == input
        assert skip_value == "true"

    @pytest.mark.parametrize(
        argnames="input", argvalues=[TEST_PACK_ZIP, CONTENT_PACKS_ZIP]
    )
    def test_upload_without_skip_validate(self, mocker, input):
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
        mock_api_client(mocker)
        # mocker.patch.object(
        #     tools, "update_server_configuration", return_value=(None, None, {})
        # )
        # mocker.patch.object(Pack, "is_server_version_ge", return_value=False)
        # mocker.patch.object(
        #     Uploader, "notify_user_should_override_packs", return_value=True
        # )

        # run
        click.Context(command=upload).invoke(upload, input=input)
        uploaded_file_path = API_CLIENT.upload_content_packs.call_args[1]["file"]

        assert str(uploaded_file_path) == input

        try:
            skip_value = API_CLIENT.upload_content_packs.call_args[1]["skip_validate"]
        except KeyError:
            skip_value = None
        assert not skip_value

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
    @pytest.mark.parametrize(argnames="is_cleanup", argvalues=[True, False])
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

        with tempfile.TemporaryDirectory() as dir:
            zip_path = Path(dir, "uploadable_packs.zip")

            click.Context(command=upload).invoke(
                upload,
                input=TEST_XSIAM_PACK,
                xsiam=False,
                zip=True,
                keep_zip=dir,
                output=Path(dir),
            )

            assert zip_path.exists() == (not is_cleanup)

            with zipfile.ZipFile(zip_path, "r") as zfile:
                for name in zfile.namelist():
                    if re.search(r"\.zip$", name) is not None:
                        # We have a zip within a zip
                        zfiledata = BytesIO(zfile.read(name))
                        with zipfile.ZipFile(zfiledata) as xsiamzipfile:
                            xsiam_pack_files = xsiamzipfile.namelist()

        # XSIAM entities are not supposed to get upload to XSOAR
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
