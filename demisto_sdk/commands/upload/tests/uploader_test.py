import json

import pytest
import demisto_client
from unittest.mock import patch

from demisto_sdk.commands.common.constants import BETA_INTEGRATIONS_DIR, INTEGRATIONS_DIR, SCRIPTS_DIR, CLASSIFIERS_DIR, \
    LAYOUTS_DIR, TEST_PLAYBOOKS_DIR
from demisto_sdk.commands.common.git_tools import git_path
from demisto_sdk.commands.common.tools import LOG_COLORS
from demisto_sdk.commands.upload.uploader import Uploader

from demisto_client.demisto_api.rest import ApiException


@pytest.fixture
def demisto_client_configure(mocker):
    mocker.patch.object(demisto_client, 'configure', return_value="object")


def test_upload_sanity(demisto_client_configure):
    integration_pckg_path = f'{git_path()}demisto_sdk/tests/test_files/content_repo_example/Integrations/Securonix/'
    integration_pckg_uploader = Uploader(input=integration_pckg_path, insecure=False, verbose=False)
    with patch.object(integration_pckg_uploader, 'client', return_value='ok'):
        assert integration_pckg_uploader.upload() == 0


def test_upload_invalid_path(demisto_client_configure):
    script_dir_path = f'{git_path()}/demisto_sdk/tests/test_files/content_repo_example/Scripts/'
    script_dir_uploader = Uploader(input=script_dir_path, insecure=False, verbose=False)
    assert script_dir_uploader.upload() == 1


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
        f"Uploaded incident field - '{incident_field_name}' - successfully",
        LOG_COLORS.NATIVE
    )

    assert print.call_args_list[0][0][0] == upload_success_message


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
    uploader._parse_error_response(response=None, error=api_exception, file_type=file_type, file_name=file_name)
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
    uploader._parse_error_response(response=None, error=api_exception, file_type=file_type, file_name=file_name)
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
    uploader._parse_error_response(response=None, error=api_exception, file_type=file_type, file_name=file_name)
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
