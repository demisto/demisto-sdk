import inspect
import json
import os
from functools import wraps
from unittest.mock import patch

import demisto_client
import pytest
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (BETA_INTEGRATIONS_DIR,
                                                   CLASSIFIERS_DIR,
                                                   INTEGRATIONS_DIR,
                                                   LAYOUTS_DIR, SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR)
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import LOG_COLORS, get_yml_paths_in_dir
from demisto_sdk.commands.unify.unifier import Unifier
from demisto_sdk.commands.upload.uploader import Uploader

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


def test_upload_integration_positive(demisto_client_configure):
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
    mocker.patch("builtins.print")
    script_name = "DummyScript.yml"
    script_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_name}"
    uploader = Uploader(input=script_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded script - '{script_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    playbook_name = "Cortex_XDR_Incident_Handling.yml"
    playbook_path = f"{git_path()}/demisto_sdk/tests/test_files/CortexXDR/Playbooks/{playbook_name}"
    uploader = Uploader(input=playbook_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded playbook - '{playbook_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    widget_name = "widget-ActiveIncidentsByRole.json"
    widget_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Widgets/{widget_name}"
    uploader = Uploader(input=widget_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded widget - '{widget_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    dashboard_name = "upload_test_dashboard.json"
    dashboard_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Dashboards/{dashboard_name}"
    uploader = Uploader(input=dashboard_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded dashboard - '{dashboard_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    layout_name = "layout-details-test_bla-V2.json"
    layout_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Layouts/{layout_name}"
    uploader = Uploader(input=layout_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded layout - '{layout_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    incident_type_name = "incidenttype-Hello_World_Alert.json"
    incident_type_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/IncidentTypes/{incident_type_name}"
    uploader = Uploader(input=incident_type_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded incident type - '{incident_type_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    classifier_name = "classifier-aws_sns_test_classifier.json"
    classifier_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Classifiers/{classifier_name}"
    uploader = Uploader(input=classifier_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded classifier - '{classifier_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    incident_field_name = "XDR_Alert_Count.json"
    incident_field_path = f"{git_path()}/demisto_sdk/tests/test_files/CortexXDR/IncidentFields/{incident_field_name}"
    uploader = Uploader(input=incident_field_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded incident field - '{incident_field_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[1][0][0] == upload_success_message


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
    integration_dir_name = "UploadTest"
    integration_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Integrations/{integration_dir_name}"
    uploader = Uploader(input=integration_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    _, integration_yml_name = get_yml_paths_in_dir(integration_path)
    uploaded_file_name = f'integration-{os.path.basename(integration_yml_name)}'
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded integration - '{uploaded_file_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[3][0][0] == upload_success_message


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
    script_dir_name = "DummyScript"
    scripts_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/{script_dir_name}"
    uploader = Uploader(input=scripts_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    uploader.upload()
    _, script_yml_name = get_yml_paths_in_dir(scripts_path)
    uploaded_file_name = f'script-{os.path.basename(script_yml_name)}'
    upload_success_message = u'{}{}{}'.format(
        LOG_COLORS.GREEN,
        f"Uploaded script - '{uploaded_file_name}': successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[3][0][0] == upload_success_message


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
    dir_name = "IncidentFields"
    incident_fields_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/{dir_name}"
    uploader = Uploader(input=incident_fields_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    assert uploader.upload() == 0
    assert len(print.call_args_list) == 7


def test_upload_pack(demisto_client_configure, mocker):
    """
    Given
        - A pack called DummyPack

    When
        - Uploading pack

    Then
        - Ensure pack is uploaded successfully
        - Ensure status code is as expected
        - Ensure amount of messages is as expected
    """
    mocker.patch("builtins.print")
    pack_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack"
    uploader = Uploader(input=pack_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    status_code = uploader.upload()
    assert status_code == 0
    assert len(print.call_args_list) == 19


def test_upload_invalid_path(demisto_client_configure):
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
    mocker.patch("builtins.print")
    file_path = f"{git_path()}/demisto_sdk/tests/test_files/Packs/DummyPack/Scripts/DummyScript/DummyScript.py"
    uploader = Uploader(input=file_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    expected_failure_message = u'{}{}{}'.format(
        LOG_COLORS.RED,
        f"\nError: Given input path: {file_path} is not valid. Input path should point to one of the following:\n"
        f"  1. Pack\n"
        f"  2. A content entity directory that is inside a pack. For example: an Integrations directory or a Layouts "
        f"directory\n"
        f"  3. Valid file that can be imported to Cortex XSOAR manually. For example a playbook:"
        f" helloWorld.yml",
        LOG_COLORS.NATIVE)
    status_code = uploader.upload()
    assert status_code == 1
    assert print.call_args_list[1][0][0] == expected_failure_message


def test_parse_error_response_ssl(demisto_client_configure, mocker):
    """
    Given
        - An empty (no given input path) Uploader object
        - An API exception raised by SSL failure

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify SSL error message printed as expected
    """
    mocker.patch("builtins.print")
    file_type = "playbook"
    file_name = "SomePlaybookName.yml"
    api_exception = ApiException(reason="[SSL: CERTIFICATE_VERIFY_FAILED]")
    uploader = Uploader(input="", insecure=False, verbose=False)
    uploader._parse_error_response(error=api_exception, file_type=file_type, file_name=file_name)
    upload_failed_message = u"{}{}{}".format(
        LOG_COLORS.RED, f"\nUpload {file_type}: {file_name} failed:", LOG_COLORS.NATIVE
    )
    api_exception_message = u'{}{}{}'.format(
        LOG_COLORS.RED,
        "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n"
        "Try running the command with --insecure flag.",
        LOG_COLORS.NATIVE
    )
    # verify exactly 2 calls to print_error
    assert len(print.call_args_list) == 2
    assert print.call_args_list[0][0][0] == upload_failed_message
    assert print.call_args_list[1][0][0] == api_exception_message


def test_parse_error_response_connection(demisto_client_configure, mocker):
    """
    Given
        - An empty (no given input path) Uploader object
        - An API exception raised by connection failure

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify connection error message printed as expected
    """
    mocker.patch("builtins.print")
    file_type = "widget"
    file_name = "SomeWidgetName.json"
    api_exception = ApiException(reason="Failed to establish a new connection:")
    uploader = Uploader(input="", insecure=False, verbose=False)
    uploader._parse_error_response(error=api_exception, file_type=file_type, file_name=file_name)
    upload_failed_message = u"{}{}{}".format(
        LOG_COLORS.RED, f"\nUpload {file_type}: {file_name} failed:", LOG_COLORS.NATIVE
    )
    api_exception_message = u'{}{}{}'.format(
        LOG_COLORS.RED,
        "Failed to establish a new connection: Connection refused.\n"
        "Try checking your BASE url configuration.",
        LOG_COLORS.NATIVE
    )
    # verify exactly 2 calls to print_error
    assert len(print.call_args_list) == 2
    assert print.call_args_list[0][0][0] == upload_failed_message
    assert print.call_args_list[1][0][0] == api_exception_message


def test_parse_error_response_forbidden(demisto_client_configure, mocker):
    """
    Given
        - An empty (no given input path) Uploader object
        - An API exception raised by forbidden failure

    When
        - Parsing error response

    Then
        - Ensure a error message is parsed successfully
        - Verify forbidden error message printed as expected
    """
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
    uploader = Uploader(input="", insecure=False, verbose=False)
    uploader._parse_error_response(error=api_exception, file_type=file_type, file_name=file_name)
    upload_failed_message = u"{}{}{}".format(
        LOG_COLORS.RED, f"\nUpload {file_type}: {file_name} failed:", LOG_COLORS.NATIVE
    )
    api_exception_message = u'{}{}{}'.format(
        LOG_COLORS.RED,
        "Error message\nTry checking your API key configuration.",
        LOG_COLORS.NATIVE
    )
    # verify exactly 2 calls to print_error
    assert len(print.call_args_list) == 2
    assert print.call_args_list[0][0][0] == upload_failed_message
    assert print.call_args_list[1][0][0] == api_exception_message


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
    dir_list = [TEST_PLAYBOOKS_DIR, BETA_INTEGRATIONS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, CLASSIFIERS_DIR, LAYOUTS_DIR]
    uploader = Uploader(input="", insecure=False, verbose=False)
    sorted_dir_list = uploader._sort_directories_based_on_dependencies(dir_list)
    assert sorted_dir_list == [INTEGRATIONS_DIR, BETA_INTEGRATIONS_DIR, SCRIPTS_DIR, TEST_PLAYBOOKS_DIR,
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
    mocker.patch("builtins.print")
    successfully_uploaded_files = [("SomeIntegrationName", "Integration")]
    uploader = Uploader(input="", insecure=False, verbose=False)
    uploader.successfully_uploaded_files = successfully_uploaded_files
    uploader._print_summary()
    expected_upload_summary_title = f'{LOG_COLORS.NATIVE}\n\nUPLOAD SUMMARY:{LOG_COLORS.NATIVE}'
    expected_successfully_uploaded_files_title = u'{}{}{}'.format(
        LOG_COLORS.GREEN, '\nSUCCESSFUL UPLOADS:', LOG_COLORS.NATIVE
    )
    expected_successfully_uploaded_files = u'{}{}{}'.format(LOG_COLORS.GREEN,
                                                            """╒═════════════════════╤═════════════╕
│ NAME                │ TYPE        │
╞═════════════════════╪═════════════╡
│ SomeIntegrationName │ Integration │
╘═════════════════════╧═════════════╛
""",
                                                            LOG_COLORS.NATIVE
                                                            )
    # verify exactly 3 calls to print_color
    assert len(print.call_args_list) == 3
    assert print.call_args_list[0][0][0] == expected_upload_summary_title
    assert print.call_args_list[1][0][0] == expected_successfully_uploaded_files_title
    assert print.call_args_list[2][0][0] == expected_successfully_uploaded_files


def test_print_summary_failed_uploaded_files(demisto_client_configure, mocker):
    """
    Given
        - An empty (no given input path) Uploader object
        - A uploaded script named SomeScriptName which failed to upload

    When
        - Printing summary of uploaded files

    Then
        - Ensure uploaded failure message is printed as expected
    """
    mocker.patch("builtins.print")
    failed_uploaded_files = [("SomeScriptName", "Script")]
    uploader = Uploader(input="", insecure=False, verbose=False)
    uploader.failed_uploaded_files = failed_uploaded_files
    uploader._print_summary()
    expected_upload_summary_title = f'{LOG_COLORS.NATIVE}\n\nUPLOAD SUMMARY:{LOG_COLORS.NATIVE}'
    expected_successfully_uploaded_files_title = u'{}{}{}'.format(
        LOG_COLORS.RED, '\nFAILED UPLOADS:', LOG_COLORS.NATIVE
    )
    expected_successfully_uploaded_files = u'{}{}{}'.format(LOG_COLORS.RED,
                                                            """╒════════════════╤════════╕
│ NAME           │ TYPE   │
╞════════════════╪════════╡
│ SomeScriptName │ Script │
╘════════════════╧════════╛
""",
                                                            LOG_COLORS.NATIVE
                                                            )
    # verify exactly 3 calls to print_color
    assert len(print.call_args_list) == 3
    assert print.call_args_list[0][0][0] == expected_upload_summary_title
    assert print.call_args_list[1][0][0] == expected_successfully_uploaded_files_title
    assert print.call_args_list[2][0][0] == expected_successfully_uploaded_files


def test_remove_temp_file(demisto_client_configure, mocker):
    """
    Given
        - A valid Integration path with `dockerimage` and `dockerimage45` fields.

    When
        - Unifying the integration.

    Then
        - Ensure the unified file created by the unifier for the upload is deleted after the process is complete.
    """
    mocker.patch("builtins.print")
    integration_pckg_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/'
    uploader = Uploader(input=integration_pckg_path, insecure=False, verbose=False)
    mocker.patch.object(uploader, 'client')
    unifier = Unifier(input=integration_pckg_path, output=integration_pckg_path)
    unified_paths = unifier.merge_script_package_to_yml()
    uploader._remove_temp_file(unified_paths[0])
    uploader._remove_temp_file(unified_paths[1])
    assert not os.path.isfile(unified_paths[0])
    assert not os.path.isfile(unified_paths[1])
