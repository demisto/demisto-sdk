import inspect
import json
from functools import wraps
from unittest.mock import MagicMock, patch

import demisto_client
import pytest
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR,
                                                   INTEGRATIONS_DIR,
                                                   LAYOUTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   FileType)
from demisto_sdk.commands.common.legacy_git_tools import git_path
from demisto_sdk.commands.common.tools import get_yml_paths_in_dir
from demisto_sdk.commands.upload.uploader import (
    Uploader, parse_error_response, print_summary,
    sort_directories_based_on_dependencies)
from packaging.version import parse

DATA = ''

# Taken from https://github.com/pytest-dev/pytest-bdd/issues/155
if not hasattr(inspect, '_orig_findsource'):
    @wraps(inspect.findsource)
    def findsource(*args, **kwargs):
        try:
            return inspect._orig_findsource(*args, **kwargs)
        except IndexError:
            raise IOError("Invalid line")

    inspect._orig_findsource = inspect.findsource
    inspect.findsource = findsource


@pytest.fixture
def demisto_client_configure(mocker):
    mocker.patch("demisto_sdk.commands.upload.uploader.get_demisto_version", return_value=parse('6.0.0'))
    mocker.patch("demisto_sdk.commands.common.content.objects.pack_objects.integration.integration.get_demisto_version",
                 return_value=parse('6.0.0'))
    mocker.patch("demisto_sdk.commands.common.content.objects.pack_objects.script.script.get_demisto_version",
                 return_value=parse('6.0.0'))
    mocker.patch("builtins.print")


def test_upload_integration_positive(demisto_client_configure, mocker):
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    integration_pckg_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/'
    integration_pckg_uploader = Uploader(input=integration_pckg_path, insecure=False, verbose=False)
    with patch.object(integration_pckg_uploader, 'client', return_value='ok'):
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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    script_name = "DummyScriptUnified.yml"
    script_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_name}"
    uploader = Uploader(input=script_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(script_name, FileType.SCRIPT.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")

    playbook_name = "Cortex_XDR_Incident_Handling.yml"
    playbook_path = f"{git_path()}/demisto_sdk/tests/test_files/CortexXDR/Playbooks/{playbook_name}"
    uploader = Uploader(input=playbook_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(playbook_name, FileType.PLAYBOOK.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")

    widget_name = "widget-ActiveIncidentsByRole.json"
    widget_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Widgets/{widget_name}"
    uploader = Uploader(input=widget_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(widget_name, FileType.WIDGET.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")

    dashboard_name = "upload_test_dashboard.json"
    dashboard_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Dashboards/{dashboard_name}"
    uploader = Uploader(input=dashboard_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [('upload_test_dashboard.json', FileType.DASHBOARD.value)] == uploader.successfully_uploaded_files


def test_upload_layout_positive(demisto_client_configure, mocker):
    """
    Given
        - A layout named layout-details-test_bla-V2 to upload

    When
        - Uploading a layout

    Then
        - Ensure layout is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    layout_name = "layout-details-test_bla-V2.json"
    layout_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/{layout_name}"
    uploader = Uploader(input=layout_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(layout_name, FileType.LAYOUT.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    incident_type_name = "incidenttype-Hello_World_Alert.json"
    incident_type_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/{incident_type_name}"
    uploader = Uploader(input=incident_type_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(incident_type_name, FileType.INCIDENT_TYPE.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    classifier_name = "classifier-aws_sns_test_classifier.json"
    classifier_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Classifiers/{classifier_name}"
    uploader = Uploader(input=classifier_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(classifier_name, FileType.OLD_CLASSIFIER.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    incident_field_name = "XDR_Alert_Count.json"
    incident_field_path = f"{git_path()}/demisto_sdk/tests/test_files/CortexXDR/IncidentFields/{incident_field_name}"
    uploader = Uploader(input=incident_field_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(incident_field_name, FileType.INCIDENT_FIELD.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value='object')
    indicator_field_name = 'dns.json'
    indicator_field_path = f'{git_path()}/demisto_sdk/tests/test_files/CortexXDR/IndicatorFields/{indicator_field_name}'
    uploader = Uploader(input=indicator_field_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(indicator_field_name, FileType.INDICATOR_FIELD.value)] == uploader.successfully_uploaded_files


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
        with open(file, 'r') as f:
            DATA = f.read()
        return

    class demisto_client_mocker():
        def import_incident_fields(self, file):
            pass

    mocker.patch.object(demisto_client, 'configure', return_value=demisto_client_mocker)

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
        with open(file, 'r') as f:
            DATA = f.read()
        return

    class demisto_client_mocker():
        def import_incident_fields(self, file):
            pass

    mocker.patch.object(demisto_client, 'configure', return_value=demisto_client_mocker)
    incident_field_name = "XDR_Alert_Count.json"
    incident_field_path = f"{git_path()}/demisto_sdk/tests/test_files/CortexXDR/IncidentFields/{incident_field_name}"
    uploader = Uploader(input=incident_field_path, insecure=False, verbose=False)
    uploader.client.import_incident_fields = MagicMock(side_effect=save_file)
    uploader.upload()

    with open(incident_field_path) as json_file:
        incident_field_data = json.load(json_file)

    assert json.loads(DATA)['incidentFields'][0] == incident_field_data


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    integration_dir_name = "UploadTest"
    integration_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Integrations/{integration_dir_name}"
    uploader = Uploader(input=integration_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    _, integration_yml_name = get_yml_paths_in_dir(integration_path)
    integration_yml_name = integration_yml_name.split('/')[-1]

    assert [(integration_yml_name, FileType.INTEGRATION.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    script_dir_name = "DummyScript"
    scripts_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_dir_name}"
    uploader = Uploader(input=scripts_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    _, script_yml_name = get_yml_paths_in_dir(scripts_path)
    uploaded_file_name = script_yml_name.split('/')[-1]

    assert [(uploaded_file_name, FileType.SCRIPT.value)] == uploader.successfully_uploaded_files


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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    mocker.patch("click.secho")
    dir_name = "IncidentFields"
    incident_fields_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/{dir_name}/"
    uploader = Uploader(input=incident_fields_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    pack_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack"
    uploader = Uploader(input=pack_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    status_code = uploader.upload()
    expected_entities = ['DummyIntegration.yml', 'UploadTest.yml', 'DummyScriptUnified.yml',
                         'DummyScript.yml', 'DummyPlaybook.yml', 'DummyTestPlaybook.yml',
                         'incidenttype-Hello_World_Alert.json', 'incidentfield-Hello_World_ID.json',
                         'incidentfield-Hello_World_Type.json', 'incidentfield-Hello_World_Status.json',
                         'classifier-aws_sns_test_classifier.json', 'widget-ActiveIncidentsByRole.json',
                         'layout-details-test_bla-V2.json', 'upload_test_dashboard.json']
    assert status_code == 0
    uploaded_objects = [obj_pair[0] for obj_pair in uploader.successfully_uploaded_files]
    for entity in expected_entities:
        assert entity in uploaded_objects


def test_upload_invalid_path(demisto_client_configure, mocker):
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    script_dir_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_not_exists/Scripts/'
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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    file_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/DummyScript/DummyScript.py"
    uploader = Uploader(input=file_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    status_code = uploader.upload()
    assert status_code == 1
    assert uploader.failed_uploaded_files[0][0] == 'DummyScript.py'


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
    message = parse_error_response(error=api_exception, file_type=file_type, file_name=file_name)
    assert message == '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n' \
                      'Try running the command with --insecure flag.'


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
    error_message = parse_error_response(error=api_exception, file_type=file_type, file_name=file_name)
    assert error_message == 'Failed to establish a new connection: Connection refused.\n' \
                            'Try checking your BASE url configuration.'


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
    api_exception.body = json.dumps({
        "status": 403,
        "error": "Error message"
    })
    message = parse_error_response(error=api_exception, file_type=file_type, file_name=file_name)
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
    dir_list = [TEST_PLAYBOOKS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, CLASSIFIERS_DIR, LAYOUTS_DIR]
    sorted_dir_list = sort_directories_based_on_dependencies(dir_list)
    assert sorted_dir_list == [INTEGRATIONS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR,
                               CLASSIFIERS_DIR, LAYOUTS_DIR]


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
    expected_upload_summary_title = '\n\nUPLOAD SUMMARY:'
    expected_successfully_uploaded_files_title = '\nSUCCESSFUL UPLOADS:'
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
    expected_upload_summary_title = '\n\nUPLOAD SUMMARY:'
    expected_failed_uploaded_files_title = '\nFAILED UPLOADS:'
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
    expected_upload_summary_title = '\n\nUPLOAD SUMMARY:'
    expected_failed_uploaded_files_title = '\nNOT UPLOADED DUE TO VERSION MISMATCH:'
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
