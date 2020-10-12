import inspect
import json
from functools import wraps
from unittest.mock import patch

import demisto_client
import pytest
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR,
                                                   INTEGRATIONS_DIR,
                                                   LAYOUTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR)
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import get_yml_paths_in_dir
from packaging.version import parse

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
    mocker.patch.object(demisto_client, 'configure', return_value="object")
    mocker.patch("demisto_sdk.commands.common.tools.get_demisto_version", return_value=parse('6.0.0'))


def test_upload_integration_positive(demisto_client_configure, mocker):
    mocker.patch("demisto_sdk.commands.common.tools.get_demisto_version", return_value=parse('6.0.0'))
    from demisto_sdk.commands.upload.new_uploader import NewUploader
    integration_pckg_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/'
    integration_pckg_uploader = NewUploader(input=integration_pckg_path, insecure=False, verbose=False)
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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    script_name = "DummyScriptUnified.yml"
    script_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_name}"
    uploader = NewUploader(input=script_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(script_name, 'Script')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    playbook_name = "Cortex_XDR_Incident_Handling.yml"
    playbook_path = f"{git_path()}/demisto_sdk/tests/test_files/CortexXDR/Playbooks/{playbook_name}"
    uploader = NewUploader(input=playbook_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(playbook_name, 'Playbook')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    widget_name = "widget-ActiveIncidentsByRole.json"
    widget_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Widgets/{widget_name}"
    uploader = NewUploader(input=widget_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(widget_name, 'Widget')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    dashboard_name = "upload_test_dashboard.json"
    dashboard_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Dashboards/{dashboard_name}"
    uploader = NewUploader(input=dashboard_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [('upload_test_dashboard.json', 'Dashboard')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    layout_name = "layout-details-test_bla-V2.json"
    layout_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/{layout_name}"
    uploader = NewUploader(input=layout_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(layout_name, 'Layout')] == uploader.successfully_uploaded_files


def test_upload_incident_type_positive(demisto_client_configure, mocker):
    """
    Given
        - An incident type named XDR_Alert_Count to upload

    When
        - Uploading incident type

    Then
        - Ensure incident type is uploaded successfully
        - Ensure success upload message is printed as expected
    """
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    incident_type_name = "incidenttype-Hello_World_Alert.json"
    incident_type_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/{incident_type_name}"
    uploader = NewUploader(input=incident_type_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(incident_type_name, 'IncidentType')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    classifier_name = "classifier-aws_sns_test_classifier.json"
    classifier_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Classifiers/{classifier_name}"
    uploader = NewUploader(input=classifier_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(classifier_name, 'OldClassifier')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    incident_field_name = "XDR_Alert_Count.json"
    incident_field_path = f"{git_path()}/demisto_sdk/tests/test_files/CortexXDR/IncidentFields/{incident_field_name}"
    uploader = NewUploader(input=incident_field_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()

    assert [(incident_field_name, 'IncidentField')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    integration_dir_name = "UploadTest"
    integration_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Integrations/{integration_dir_name}"
    uploader = NewUploader(input=integration_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    _, integration_yml_name = get_yml_paths_in_dir(integration_path)
    integration_yml_name = integration_yml_name.split('/')[-1]

    assert [(integration_yml_name, 'Integration')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    script_dir_name = "DummyScript"
    scripts_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_dir_name}"
    uploader = NewUploader(input=scripts_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    _, script_yml_name = get_yml_paths_in_dir(scripts_path)
    uploaded_file_name = script_yml_name.split('/')[-1]

    assert [(uploaded_file_name, 'Script')] == uploader.successfully_uploaded_files


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
    mocker.patch("builtins.print")
    mocker.patch("click.secho")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    dir_name = "IncidentFields"
    incident_fields_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/{dir_name}/"
    uploader = NewUploader(input=incident_fields_path, insecure=False, verbose=False)
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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    pack_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack"
    uploader = NewUploader(input=pack_path, insecure=False, verbose=False)
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


def test_upload_invalid_path(demisto_client_configure):
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    script_dir_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_not_exists/Scripts/'
    script_dir_uploader = NewUploader(input=script_dir_path, insecure=False, verbose=False)
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
    mocker.patch("builtins.print")
    # This is imported here in order to apply the mock of `get_demisto_version`
    from demisto_sdk.commands.upload.new_uploader import NewUploader

    file_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/DummyScript/DummyScript.py"
    uploader = NewUploader(input=file_path, insecure=False, verbose=False)
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
    mocker.patch("builtins.print")
    from demisto_sdk.commands.upload.new_uploader import parse_error_response
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
    from demisto_sdk.commands.upload.new_uploader import parse_error_response
    mocker.patch("builtins.print")
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
    from demisto_sdk.commands.upload.new_uploader import parse_error_response

    mocker.patch("builtins.print")
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
    from demisto_sdk.commands.upload.new_uploader import sort_directories_based_on_dependencies
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
    from demisto_sdk.commands.upload.new_uploader import print_summary

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
    assert secho.call_args_list[1].kwargs.get('fg') == 'green'
    assert secho.call_args_list[2][0][0] == expected_successfully_uploaded_files
    assert secho.call_args_list[2].kwargs.get('fg') == 'green'


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
    from demisto_sdk.commands.upload.new_uploader import print_summary

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
    assert secho.call_args_list[1].kwargs.get('fg') == 'bright_red'
    assert secho.call_args_list[2][0][0] == expected_failed_uploaded_files
    assert secho.call_args_list[2].kwargs.get('fg') == 'bright_red'


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
    mocker.patch("demisto_sdk.commands.common.tools.get_demisto_version", return_value=parse('6.0.0'))
    from demisto_sdk.commands.upload.new_uploader import print_summary

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
    assert secho.call_args_list[1].kwargs.get('fg') == 'yellow'
    assert secho.call_args_list[2][0][0] == expected_failed_uploaded_files
    assert secho.call_args_list[2].kwargs.get('fg') == 'yellow'
