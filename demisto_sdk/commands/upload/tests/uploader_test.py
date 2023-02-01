import inspect
import re
import shutil
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
from packaging.version import parse

from demisto_sdk.__main__ import main, upload
from demisto_sdk.commands.common import constants
from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR,
    INTEGRATIONS_DIR,
    LAYOUTS_DIR,
    SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR,
    FileType,
)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import (
    DELETE_VERIFY_KEY_ACTION,
    TURN_VERIFICATION_ERROR_MSG,
    Pack,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yml_paths_in_dir, src_root
from demisto_sdk.commands.content_graph.objects.integration_script import (
    IntegrationScript,
)
from demisto_sdk.commands.test_content import tools
from demisto_sdk.commands.upload import uploader
from demisto_sdk.commands.upload.uploader import (
    ItemDetacher,
    Uploader,
    parse_error_response,
    print_summary,
    sort_directories_based_on_dependencies,
)
from TestSuite.test_tools import ChangeCWD

json = JSON_Handler()


DATA = ""

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
        return_value=parse("6.0.0"),
    )
    mocker.patch(
        "demisto_sdk.commands.common.content.objects.pack_objects.integration.integration.get_demisto_version",
        return_value=parse("6.0.0"),
    )
    mocker.patch(
        "demisto_sdk.commands.common.content.objects.pack_objects.script.script.get_demisto_version",
        return_value=parse("6.0.0"),
    )
    mocker.patch("builtins.print")


def test_upload_integration_positive(demisto_client_configure, mocker):
    mocker.patch.object(demisto_client, "configure", return_value="object")
    mocker.patch.object(
        IntegrationScript, "get_supported_native_images", return_value=[]
    )
    integration_pckg_path = f"{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/"
    integration_pckg_uploader = Uploader(
        input=integration_pckg_path, insecure=False, verbose=False
    )
    with patch.object(integration_pckg_uploader, "client", return_value="ok"):
        assert integration_pckg_uploader.upload() == 0


def test_upload_script_positive(demisto_client_configure, mocker):
    """
    Given
        - A script named EntryWidgetNumberHostsXDR to upload

    When
        - Uploading a script

    Then
        - Ensure script is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    script_name = "DummyScriptUnified.yml"
    script_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_name}"
    uploader = Uploader(input=script_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (script_name, FileType.SCRIPT.value)
    ] == uploader.successfully_uploaded_files


def test_upload_playbook_positive(demisto_client_configure, mocker):
    """
    Given
        - A playbook named Cortex_XDR_Incident_Handling to upload

    When
        - Uploading a playbook

    Then
        - Ensure playbook is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")

    playbook_name = "Cortex_XDR_Incident_Handling.yml"
    playbook_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/CortexXDR/Playbooks/{playbook_name}"
    uploader = Uploader(input=playbook_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (playbook_name, FileType.PLAYBOOK.value)
    ] == uploader.successfully_uploaded_files


def test_upload_widget_positive(demisto_client_configure, mocker):
    """
    Given
        - A widget named ActiveIncidentsByRole to upload

    When
        - Uploading a widget

    Then
        - Ensure widget is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")

    widget_name = "widget-ActiveIncidentsByRole.json"
    widget_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Widgets/{widget_name}"
    uploader = Uploader(input=widget_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (widget_name, FileType.WIDGET.value)
    ] == uploader.successfully_uploaded_files


def test_upload_dashboard_positive(demisto_client_configure, mocker):
    """
    Given
        - A dashboard named upload_test_dashboard.json to upload

    When
        - Uploading a dashboard

    Then
        - Ensure dashboard is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")

    dashboard_name = "upload_test_dashboard.json"
    dashboard_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Dashboards/{dashboard_name}"
    uploader = Uploader(input=dashboard_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        ("upload_test_dashboard.json", FileType.DASHBOARD.value)
    ] == uploader.successfully_uploaded_files


def test_upload_layout_positive(demisto_client_configure, mocker):
    """
    Given
        - A layout named layout-details-test_bla-V2 to upload

    When
        - Uploading a layout

    Then
        - Ensure layout is uploaded successfully
        - Ensure success upload message is printed as expected
        - Ensure that _unify isn't called.
    """
    from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import (
        LayoutObject,
    )

    mocker.patch.object(demisto_client, "configure", return_value="object")
    unify_mocker = mocker.patch.object(LayoutObject, "_unify")

    layout_name = "layout-details-test_bla-V2.json"
    layout_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/{layout_name}"

    uploader = Uploader(input=layout_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert not unify_mocker.called
    assert [
        (layout_name, FileType.LAYOUT.value)
    ] == uploader.successfully_uploaded_files


def test_upload_layout_container_positive(demisto_client_configure, mocker):
    """
    Given
        - layout container

    When
        - Uploading a layout-container

    Then
        - Ensure layout-container is uploaded successfully
        - Ensure that _unify is called.
    """
    from demisto_sdk.commands.common.content.objects.pack_objects.layout.layout import (
        LayoutObject,
    )

    mocker.patch.object(demisto_client, "configure", return_value="object")
    unify_mocker = mocker.patch.object(LayoutObject, "_unify")

    layout_name = "layoutscontainer-test.json"
    layout_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/{layout_name}"

    uploader = Uploader(input=layout_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert unify_mocker.called
    assert [
        (layout_name, FileType.LAYOUTS_CONTAINER.value)
    ] == uploader.successfully_uploaded_files


def test_upload_incident_type_positive(demisto_client_configure, mocker):
    """
    Given
        - An incident type named Hello_World_Alert to upload

    When
        - Uploading incident type

    Then
        - Ensure incident type is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    incident_type_name = "incidenttype-Hello_World_Alert.json"
    incident_type_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/{incident_type_name}"
    uploader = Uploader(input=incident_type_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (incident_type_name, FileType.INCIDENT_TYPE.value)
    ] == uploader.successfully_uploaded_files


def test_upload_classifier_positive(demisto_client_configure, mocker):
    """
    Given
        - A classifier type named XDR_Alert_Count to upload

    When
        - Uploading classifier

    Then
        - Ensure classifier is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    classifier_name = "classifier-aws_sns_test_classifier.json"
    classifier_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Classifiers/{classifier_name}"
    uploader = Uploader(input=classifier_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (classifier_name, FileType.OLD_CLASSIFIER.value)
    ] == uploader.successfully_uploaded_files


def test_upload_incident_field_positive(demisto_client_configure, mocker):
    """
    Given
        - An incident field named XDR_Alert_Count to upload

    When
        - Uploading incident field

    Then
        - Ensure incident field is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    incident_field_name = "XDR_Alert_Count.json"
    incident_field_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/CortexXDR/IncidentFields/{incident_field_name}"
    uploader = Uploader(input=incident_field_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (incident_field_name, FileType.INCIDENT_FIELD.value)
    ] == uploader.successfully_uploaded_files


def test_upload_indicator_field_positive(demisto_client_configure, mocker):
    """
    Given
        - An indicator field named DNS to upload
    When
        - Uploading indicator field
    Then
        - Ensure indicator field is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    indicator_field_name = "dns.json"
    indicator_field_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/CortexXDR/IndicatorFields/{indicator_field_name}"
    uploader = Uploader(input=indicator_field_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (indicator_field_name, FileType.INDICATOR_FIELD.value)
    ] == uploader.successfully_uploaded_files


def test_upload_reputation_positive(demisto_client_configure, mocker):
    """
    Given
        - A reputation named SampleIndicatorType to upload

    When
        - Uploading a reputation

    Then
        - Ensure reputation is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")

    reputation_name = "SampleIndicatorType.json"
    reputation_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/CortexXDR/IndicatorTypes/{reputation_name}"
    uploader = Uploader(input=reputation_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()

    assert [
        (reputation_name, FileType.REPUTATION.value)
    ] == uploader.successfully_uploaded_files


def test_upload_report_positive(demisto_client_configure, mocker, repo):
    """
    Given
        - A report to upload

    When
        - Uploading a report

    Then
        - Ensure report is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    pack = repo.create_pack("pack")
    report = pack.create_report("test-report")
    report.write_json({"id": "dummy-report", "orientation": "portrait"})
    with ChangeCWD(repo.path):
        uploader = Uploader(input=report.path, insecure=False, verbose=False)
        mocker.patch.object(uploader, "client")
        uploader.upload()
    assert [
        (report.name, FileType.REPORT.value)
    ] == uploader.successfully_uploaded_files


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

    incident_type_name = "incidenttype-Hello_World_Alert.json"
    incident_type_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/{incident_type_name}"
    uploader = Uploader(input=incident_type_path, insecure=False, verbose=False)
    uploader.client.import_incident_types_handler = MagicMock(side_effect=save_file)
    uploader.upload()

    with open(incident_type_path) as json_file:
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
    incident_field_name = "XDR_Alert_Count.json"
    incident_field_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/CortexXDR/IncidentFields/{incident_field_name}"
    uploader = Uploader(input=incident_field_path, insecure=False, verbose=False)
    uploader.client.import_incident_fields = MagicMock(side_effect=save_file)
    uploader.upload()

    with open(incident_field_path) as json_file:
        incident_field_data = json.load(json_file)

    assert json.loads(DATA)["incidentFields"][0] == incident_field_data


def test_upload_an_integration_directory(demisto_client_configure, mocker):
    """
    Given
        - An integration directory called UploadTest

    When
        - Uploading an integration

    Then
        - Ensure integration is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    mocker.patch.object(
        IntegrationScript, "get_supported_native_images", return_value=[]
    )
    integration_dir_name = "UploadTest"
    integration_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Integrations/{integration_dir_name}"
    uploader = Uploader(input=integration_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()
    _, integration_yml_name = get_yml_paths_in_dir(integration_path)
    integration_yml_name = integration_yml_name.split("/")[-1]

    assert [
        (integration_yml_name, FileType.INTEGRATION.value)
    ] == uploader.successfully_uploaded_files


def test_upload_a_script_directory(demisto_client_configure, mocker):
    """
    Given
        - A script directory called DummyScript

    When
        - Uploading an script

    Then
        - Ensure script is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    mocker.patch.object(
        IntegrationScript, "get_supported_native_images", return_value=[]
    )
    script_dir_name = "DummyScript"
    scripts_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_dir_name}"
    uploader = Uploader(input=scripts_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    uploader.upload()
    _, script_yml_name = get_yml_paths_in_dir(scripts_path)
    uploaded_file_name = script_yml_name.split("/")[-1]

    assert [
        (uploaded_file_name, FileType.SCRIPT.value)
    ] == uploader.successfully_uploaded_files


def test_upload_incident_fields_directory(demisto_client_configure, mocker):
    """
    Given
        - An incident fields directory called DummyScript

    When
        - Uploading incident fields

    Then
        - Ensure incident fields are uploaded successfully
        - Ensure status code is as expected
        - Ensure amount of messages is as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    mocker.patch("click.secho")
    dir_name = "IncidentFields"
    incident_fields_path = (
        f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/{dir_name}/"
    )
    uploader = Uploader(input=incident_fields_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    assert uploader.upload() == 0
    assert len(uploader.successfully_uploaded_files) == 3


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
    pack_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack"
    uploader = Uploader(input=pack_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    status_code = uploader.upload()
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
        "layout-details-test_bla-V2.json",
        "upload_test_dashboard.json",
    ]
    assert status_code == 0
    uploaded_objects = [
        obj_pair[0] for obj_pair in uploader.successfully_uploaded_files
    ]
    for entity in expected_entities:
        assert entity in uploaded_objects


def test_upload_invalid_path(demisto_client_configure, mocker):
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

    mocker.patch.object(
        demisto_client, "configure", return_value=demisto_client_mocker()
    )
    script_dir_path = (
        f"{git_path()}/demisto_sdk/tests/test_files/content_repo_not_exists/Scripts/"
    )
    script_dir_uploader = Uploader(input=script_dir_path, insecure=False, verbose=False)
    assert script_dir_uploader.upload() == 1


def test_file_not_supported(demisto_client_configure, mocker):
    """
    Given
        - A not supported (.py) file

    When
        - Uploading a file

    Then
        - Ensure uploaded failure message is printed as expected
    """
    mocker.patch.object(demisto_client, "configure", return_value="object")
    file_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/DummyScript/DummyScript.py"
    uploader = Uploader(input=file_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, "client")
    status_code = uploader.upload()
    assert status_code == 1
    assert uploader.failed_uploaded_files[0][0] == "DummyScript.py"


def test_parse_error_response_ssl(demisto_client_configure, mocker):
    """
    Given
        - An API exception raised by SSL failure

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify SSL error message printed as expected
    """
    file_type = "playbook"
    file_name = "SomePlaybookName.yml"
    api_exception = ApiException(reason="[SSL: CERTIFICATE_VERIFY_FAILED]")
    message = parse_error_response(
        error=api_exception, file_type=file_type, file_name=file_name
    )
    assert (
        message
        == "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n"
        "Try running the command with --insecure flag."
    )


def test_parse_error_response_connection(demisto_client_configure, mocker):
    """
    Given
        - An API exception raised by connection failure

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify connection error message printed as expected
    """
    file_type = "widget"
    file_name = "SomeWidgetName.json"
    api_exception = ApiException(reason="Failed to establish a new connection:")
    error_message = parse_error_response(
        error=api_exception, file_type=file_type, file_name=file_name
    )
    assert (
        error_message == "Failed to establish a new connection: Connection refused.\n"
        "Try checking your BASE url configuration."
    )


def test_parse_error_response_forbidden(demisto_client_configure, mocker):
    """
    Given
        - An API exception raised by forbidden failure

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify forbidden error message printed as expected
    """
    file_type = "incident field"
    file_name = "SomeIncidentFieldName.json"
    api_exception = ApiException(
        reason="Forbidden",
    )
    api_exception.body = json.dumps({"status": 403, "error": "Error message"})
    message = parse_error_response(
        error=api_exception, file_type=file_type, file_name=file_name
    )
    assert message == "Error message\nTry checking your API key configuration."


def test_sort_directories_based_on_dependencies(demisto_client_configure):
    """
    Given
        - An empty (no given input path) Uploader object
        - List of non-sorted (based on dependencies) content directories

    When
        - Running sort_directories_based_on_dependencies on the list

    Then
        - Ensure a sorted listed of the directories is returned
    """
    dir_list = [
        TEST_PLAYBOOKS_DIR,
        INTEGRATIONS_DIR,
        SCRIPTS_DIR,
        CLASSIFIERS_DIR,
        LAYOUTS_DIR,
    ]
    sorted_dir_list = sort_directories_based_on_dependencies(dir_list)
    assert sorted_dir_list == [
        INTEGRATIONS_DIR,
        SCRIPTS_DIR,
        TEST_PLAYBOOKS_DIR,
        CLASSIFIERS_DIR,
        LAYOUTS_DIR,
    ]


def test_print_summary_successfully_uploaded_files(demisto_client_configure, mocker):
    """
    Given
        - An empty (no given input path) Uploader object
        - A successfully uploaded integration named SomeIntegrationName

    When
        - Printing summary of uploaded files

    Then
        - Ensure uploaded successfully message is printed as expected
    """
    mocker.patch("click.secho")
    from click import secho

    successfully_uploaded_files = [("SomeIntegrationName", "Integration")]

    print_summary(successfully_uploaded_files, [], [])
    expected_upload_summary_title = "\n\nUPLOAD SUMMARY:"
    expected_successfully_uploaded_files_title = "\nSUCCESSFUL UPLOADS:"
    expected_successfully_uploaded_files = """╒═════════════════════╤═════════════╕
│ NAME                │ TYPE        │
╞═════════════════════╪═════════════╡
│ SomeIntegrationName │ Integration │
╘═════════════════════╧═════════════╛
"""
    # verify exactly 3 calls to print_color
    assert secho.call_count == 3
    assert secho.call_args_list[0][0][0] == expected_upload_summary_title
    assert secho.call_args_list[1][0][0] == expected_successfully_uploaded_files_title
    assert secho.call_args_list[2][0][0] == expected_successfully_uploaded_files


def test_print_summary_failed_uploaded_files(demisto_client_configure, mocker):
    """
    Given
        - A uploaded script named SomeScriptName which failed to upload

    When
        - Printing summary of uploaded files

    Then
        - Ensure uploaded failure message is printed as expected
    """
    mocker.patch("click.secho")
    from click import secho

    failed_uploaded_files = [("SomeScriptName", "Script", "Some Error")]
    print_summary([], [], failed_uploaded_files)
    expected_upload_summary_title = "\n\nUPLOAD SUMMARY:"
    expected_failed_uploaded_files_title = "\nFAILED UPLOADS:"
    expected_failed_uploaded_files = """╒════════════════╤════════╤════════════╕
│ NAME           │ TYPE   │ ERROR      │
╞════════════════╪════════╪════════════╡
│ SomeScriptName │ Script │ Some Error │
╘════════════════╧════════╧════════════╛
"""
    # verify exactly 3 calls to print_color
    assert secho.call_count == 3
    assert secho.call_args_list[0][0][0] == expected_upload_summary_title
    assert secho.call_args_list[1][0][0] == expected_failed_uploaded_files_title
    assert secho.call_args_list[2][0][0] == expected_failed_uploaded_files


def test_print_summary_unuploaded_files(demisto_client_configure, mocker):
    """
    Given
        - A uploaded script named SomeScriptName which did not upload due to version mismatch

    When
        - Printing summary of uploaded files

    Then
        - Ensure uploaded unuploaded message is printed as expected
    """
    mocker.patch("click.secho")
    from click import secho

    unploaded_files = [("SomeScriptName", "Script", "6.0.0", "0.0.0", "5.0.0")]
    print_summary([], unploaded_files, [])
    expected_upload_summary_title = "\n\nUPLOAD SUMMARY:"
    expected_failed_uploaded_files_title = "\nNOT UPLOADED DUE TO VERSION MISMATCH:"
    expected_failed_uploaded_files = """╒════════════════╤════════╤═════════════════╤═════════════════════╤═══════════════════╕
│ NAME           │ TYPE   │ XSOAR Version   │ FILE_FROM_VERSION   │ FILE_TO_VERSION   │
╞════════════════╪════════╪═════════════════╪═════════════════════╪═══════════════════╡
│ SomeScriptName │ Script │ 6.0.0           │ 0.0.0               │ 5.0.0             │
╘════════════════╧════════╧═════════════════╧═════════════════════╧═══════════════════╛
"""
    # verify exactly 3 calls to print_color
    assert secho.call_count == 3
    assert secho.call_args_list[0][0][0] == expected_upload_summary_title
    assert secho.call_args_list[1][0][0] == expected_failed_uploaded_files_title
    assert secho.call_args_list[2][0][0] == expected_failed_uploaded_files


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
    mocker.patch.object(uploader, "get_demisto_version", return_value=parse("6.0.0"))


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

    def test_zip_and_upload(self, mocker):
        """
        Given:
            - name of pack in content and the zip flag is on
        When:
            - call to upload command
        Then:
            - validate the zip file was created and pass to the zipped_pack_uploader method
        """
        # prepare
        mock_api_client(mocker)
        mocker.patch.object(Uploader, "zipped_pack_uploader")

        # run
        click.Context(command=upload).invoke(upload, input=TEST_PACK, zip=True)

        # validate
        assert (
            "uploadable_packs.zip" in Uploader.zipped_pack_uploader.call_args[1]["path"]
        )

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

    @pytest.mark.parametrize(argnames="input", argvalues=[INVALID_ZIP, None])
    def test_upload_invalid_zip_path(self, mocker, input):
        """
        Given:
            - invalid path in the input argument
        When:
            - run the upload zipped pack
        Then:
            - validate the error msg
        """
        # prepare
        mock_api_client(mocker)
        mocker.patch("click.secho")

        # run
        status = click.Context(command=upload).invoke(upload, input=input)

        # validate
        status == 1
        uploader.click.secho.call_args_list[1].args == INVALID_ZIP_ERROR.format(
            path=input
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
        exp_err_msg = TURN_VERIFICATION_ERROR_MSG.format(
            action=DELETE_VERIFY_KEY_ACTION
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
    def test_upload_xsiam_pack_to_xsoar(self, mocker, is_cleanup):
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
        # prepare
        mock_api_client(mocker)
        mocker.patch.object(Uploader, "zipped_pack_uploader")

        # run
        click.Context(command=upload).invoke(
            upload, input=TEST_XSIAM_PACK, xsiam=False, zip=True
        )

        zip_file_path = Uploader.zipped_pack_uploader.call_args[1]["path"]
        assert "uploadable_packs.zip" in zip_file_path
        if is_cleanup:
            assert not Path.exists(Path(zip_file_path)), "zip should be cleaned up"
            return
        with zipfile.ZipFile(zip_file_path, "r") as zfile:
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
        mocker.patch("click.secho")
        from click import secho

        mock_api_client(mocker)
        mocker.patch.object(
            API_CLIENT,
            "generic_request",
            return_value=[json.dumps([{"name": "TestPack"}])],
        )

        ItemDetacher.detach_item(
            ItemDetacher(API_CLIENT), file_id="file", file_path="Scripts/file_path"
        )

        assert secho.call_count == 1
        assert secho.call_args_list[0][0][0] == "\nFile: file was detached"

    def test_extract_items_from_dir(self, mocker, repo):
        repo = repo.setup_one_pack(name="Pack")
        list_items = ItemDetacher(
            client=API_CLIENT, file_path=repo.path
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
            ItemDetacher(client=API_CLIENT).is_valid_file_for_detach(
                file_path=file_path
            )
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
            ItemDetacher(client=API_CLIENT).find_item_type_to_detach(
                file_path=file_path
            )
            == res
        )

    def test_find_item_id_to_detach(self, repo):
        pack = repo.create_pack("Pack1")
        playbook1 = pack.create_playbook("MyPlay1")
        playbook1.create_default_playbook()
        assert (
            ItemDetacher(
                client=API_CLIENT, file_path=f"{playbook1.path}/MyPlay1.yml"
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
            client=API_CLIENT, file_path=repo.path
        ).detach_item_manager()
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
        ).detach_item_manager()
        assert len(detached_items_ids) == 1
        assert detached_items_ids == ["Pack_playbook"]


def exception_raiser(**kwargs):
    raise Exception()
