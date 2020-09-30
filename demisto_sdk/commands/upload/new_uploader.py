import json
import os
from tempfile import NamedTemporaryFile
from typing import List, Tuple
import click

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (CONTENT_ENTITIES_DIRS,
                                                   CONTENT_ENTITY_UPLOAD_ORDER,
                                                   INTEGRATIONS_DIR, PACKS_DIR,
                                                   SCRIPTS_DIR, FileType)
from demisto_sdk.commands.common.tools import (
    LOG_COLORS, find_type, get_child_directories, get_child_files, get_json,
    get_parent_directory_name, is_path_of_classifier_directory,
    is_path_of_dashboard_directory, is_path_of_incident_field_directory,
    is_path_of_incident_type_directory, is_path_of_integration_directory,
    is_path_of_layout_directory, is_path_of_playbook_directory,
    is_path_of_script_directory, is_path_of_test_playbook_directory,
    is_path_of_widget_directory, print_color, print_error, print_v, get_demisto_version, server_version_compare)
from demisto_sdk.commands.unify.unifier import Unifier
from tabulate import tabulate
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from packaging.version import LegacyVersion, Version, parse

# These are the class names of the objects in demisto_sdk.commands.common.content.objects
UPLOAD_SUPPORTED_ENTITIES = ['Integration', 'Script', 'Playbook', 'Widget', 'IncidentType', 'Classifier',
                             'OldClassifier', 'Layout', 'LayoutsContainer', 'Dashboard', 'IncidentField']


class NewUploader:
    """Upload a pack specified in self.infile to a remote Cortex XSOAR instance.
        Attributes:
            path (str): The path of a pack / directory / file to upload.
            verbose (bool): Whether to output a detailed response.
            client (DefaultApi): Demisto-SDK client object.
        """

    def __init__(self, input: str, insecure: bool = False, verbose: bool = False):
        self.path = input
        self.log_verbose = verbose
        self.client = demisto_client.configure(verify_ssl=not insecure)
        self.successfully_uploaded_files: List[Tuple[str, str]] = []
        self.failed_uploaded_files: List[Tuple[str, str]] = []
        self.unuploaded_due_to_version: List[Tuple[str, str, Version, Version, Version]] = []
        self.demisto_version = get_demisto_version(self.client)

    def upload(self):
        """Upload the pack / directory / file to the remote Cortex XSOAR instance.
        """
        status_code = 0
        print(f"Uploading {self.path} ...")
        if not os.path.exists(self.path):
            print_error(f'Error: Given input path: {self.path} does not exist')
            status_code = 1

        # Uploading a file
        elif os.path.isfile(self.path):
            status_code = status_code or file_uploader(**self.__dict__)

        print_summary(self.successfully_uploaded_files, self.unuploaded_due_to_version, self.failed_uploaded_files)
        return status_code
;

def file_uploader(path: str, client: demisto_client, demisto_version: Version, log_verbose: bool,
                  failed_uploaded_files: List[Tuple[str, str]],
                  unuploaded_due_to_version: List[Tuple[str, str, Version, Version, Version]],
                  successfully_uploaded_files: List[Tuple[str, str]]) -> int:
    upload_object = path_to_pack_object(path)
    file_name = upload_object.path.name
    entity_type = type(upload_object).__name__

    if entity_type in UPLOAD_SUPPORTED_ENTITIES:
        if upload_object.from_version < demisto_version < upload_object.to_version:
            try:
                result = upload_object.upload(client)
                # Print results
                print_v(f'Result:\n{result.to_str()}', log_verbose)
                click.secho(f'Uploaded classifier - \'{os.path.basename(path)}\': successfully', fg='green')
                return True
            except Exception as err:
                parse_error_response(err, 'classifier', file_name)
                failed_uploaded_files.append((file_name, entity_type))
                return 1
        else:
            click.secho(f"Input path {path} is not uploading due to version mismatch.\n"
                        f"XSOAR version is: {demisto_version} while the file's version is "
                        f"{upload_object.from_version} - {upload_object.to_version}", fg='bright_red')
            unuploaded_due_to_version.append((file_name, entity_type, demisto_version,
                                                   upload_object.from_version, upload_object.to_version))
            return 1
    else:
        click.secho(
            f'\nError: Given input path: {path} is not valid. '
            f'Input path should point to one of the following:\n'
            f'  1. Pack\n'
            f'  2. A content entity directory that is inside a pack. For example: an Integrations directory or '
            f'a Layouts directory\n'
            f'  3. Valid file that can be imported to Cortex XSOAR manually. '
            f'For example a playbook: helloWorld.yml',
            fg='bright_red'
        )
        failed_uploaded_files.append((file_name, 'Classifier'))
        return 1

    def entity_dir_uploader(self):
        pass

    def pack_uploader(self):
        pass

def parse_error_response(error: ApiException, file_type: str, file_name: str):
    """Parses error message from exception raised in call to client to upload a file

    error (ApiException): The exception which was raised in call in to client
    file_type (str): The file type which was attempted to be uploaded
    file_name (str): The file name which was attempted to be uploaded
    """
    message = error
    if hasattr(error, 'reason'):
        if '[SSL: CERTIFICATE_VERIFY_FAILED]' in str(error.reason):
            message = '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n' \
                      'Try running the command with --insecure flag.'

        elif 'Failed to establish a new connection:' in str(error.reason):
            message = 'Failed to establish a new connection: Connection refused.\n' \
                      'Try checking your BASE url configuration.'

        elif error.reason in ('Bad Request', 'Forbidden'):
            error_body = json.loads(error.body)
            message = error_body.get('error')

            if error_body.get('status') == 403:
                message += '\nTry checking your API key configuration.'
    click.secho(str(f'\nUpload {file_type}: {file_name} failed:'), fg='bright_red')
    click.secho(str(message), fg='bright_red')


def print_summary(successfully_uploaded_files, unuploaded_due_to_version, failed_uploaded_files):
    """Prints uploaded files summary
    Successful uploads grid based on `successfully_uploaded_files` attribute in green color
    Failed uploads grid based on `failed_uploaded_files` attribute in red color
    """
    print_color('\n\nUPLOAD SUMMARY:', LOG_COLORS.NATIVE)
    if successfully_uploaded_files:
        print_color('\nSUCCESSFUL UPLOADS:', LOG_COLORS.GREEN)
        print_color(tabulate(successfully_uploaded_files, headers=['NAME', 'TYPE'],
                             tablefmt="fancy_grid") + '\n', LOG_COLORS.GREEN)
    if unuploaded_due_to_version:
        print_color('\nNOT UPLOADED DUE TO VERSION MISMATCH:', LOG_COLORS.YELLOW)
        print_color(tabulate(unuploaded_due_to_version, headers=['NAME', 'TYPE', 'XSOAR Version',
                                                                      'FILE_FROM_VERSION', 'FILE_TO_VERSION'],
                             tablefmt="fancy_grid") + '\n', LOG_COLORS.YELLOW)
    if failed_uploaded_files:
        print_color('\nFAILED UPLOADS:', LOG_COLORS.RED)
        print_color(tabulate(failed_uploaded_files, headers=['NAME', 'TYPE'],
                             tablefmt="fancy_grid") + '\n', LOG_COLORS.RED)
