import glob
import json
import os
from typing import List, Tuple, Union

import click
import demisto_client
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (CONTENT_ENTITIES_DIRS,
                                                   INTEGRATIONS_DIR, PACKS_DIR,
                                                   SCRIPTS_DIR)
from demisto_sdk.commands.common.content.objects.abstract_objects import (
    JSONObject, YAMLObject)
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import (LOG_COLORS, get_demisto_version,
                                               get_parent_directory_name,
                                               print_color, print_error,
                                               print_v)
from packaging.version import Version
from tabulate import tabulate

# These are the class names of the objects in demisto_sdk.commands.common.content.objects
UPLOAD_SUPPORTED_ENTITIES = ['Integration', 'Script', 'Playbook', 'Widget', 'IncidentType', 'Classifier',
                             'OldClassifier', 'Layout', 'LayoutsContainer', 'Dashboard', 'IncidentField']

UNIFIED_ENTITIES_DIR = [INTEGRATIONS_DIR, SCRIPTS_DIR]


class NewUploader:
    """Upload a pack specified in self.infile to a remote Cortex XSOAR instance.
        Attributes:
            path (str): The path of a pack / directory / file to upload.
            verbose (bool): Whether to output a detailed response.
            client (DefaultApi): Demisto-SDK client object.
        """

    def __init__(self, input: str, insecure: bool = False, verbose: bool = False, override: bool = False):
        self.path = input
        self.log_verbose = verbose
        self.client = demisto_client.configure(verify_ssl=not insecure)
        self.successfully_uploaded_files: List[Tuple[str, str]] = []
        self.failed_uploaded_files: List[Tuple[str, str, str]] = []
        self.unuploaded_due_to_version: List[Tuple[str, str, Version, Version, Version]] = []
        self.demisto_version = get_demisto_version(self.client)
        self.override = override

    def upload(self):
        """Upload the pack / directory / file to the remote Cortex XSOAR instance.
        """
        status_code = 0
        print(f"Uploading {self.path} ...")
        if not os.path.exists(self.path):
            print_error(f'Error: Given input path: {self.path} does not exist')
            return 1

        # Uploading a file
        elif os.path.isfile(self.path):
            status_code = self.file_uploader(self.path) or status_code

        # Uploading an entity directory
        elif os.path.isdir(self.path):
            parent_dir_name = get_parent_directory_name(self.path)
            if parent_dir_name in UNIFIED_ENTITIES_DIR:
                status_code = self.unified_entity_uploader(self.path) or status_code
            elif os.path.basename(self.path.rstrip('/')) in CONTENT_ENTITIES_DIRS:
                status_code = self.entity_dir_uploader(self.path) or status_code
            elif parent_dir_name == PACKS_DIR:
                status_code = self.pack_uploader(self.path) or status_code

        print_summary(self.successfully_uploaded_files, self.unuploaded_due_to_version, self.failed_uploaded_files)
        return status_code

    def file_uploader(self, path: str) -> int:
        """
        Upload a file.
        Args:
            path: The path of the file to upload. The rest of the parameters are taken from self.

        Returns:

        """
        upload_object: Union[YAMLObject, JSONObject] = path_to_pack_object(path)
        file_name = upload_object.path.name  # type: ignore
        entity_type = type(upload_object).__name__

        if entity_type in UPLOAD_SUPPORTED_ENTITIES:
            if upload_object.from_version < self.demisto_version < upload_object.to_version:  # type: ignore
                try:
                    if entity_type in ['Integration', 'Script', 'Playbook']:
                        result = upload_object.upload(self.client, override=self.override)  # type: ignore
                    else:
                        result = upload_object.upload(self.client)  # type: ignore
                    # Print results
                    print_v(f'Result:\n{result.to_str()}', self.log_verbose)
                    click.secho(f'Uploaded {entity_type} - \'{os.path.basename(path)}\': successfully', fg='green')
                    self.successfully_uploaded_files.append((file_name, entity_type))
                    return True
                except Exception as err:
                    message = parse_error_response(err, 'classifier', file_name)
                    self.failed_uploaded_files.append((file_name, entity_type, message))
                    return 1
            else:
                click.secho(f"Input path {path} is not uploading due to version mismatch.\n"
                            f"XSOAR version is: {self.demisto_version} while the file's version is "
                            f"{upload_object.from_version} - {upload_object.to_version}", fg='bright_red')
                self.unuploaded_due_to_version.append((file_name, entity_type, self.demisto_version,
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
            self.failed_uploaded_files.append((file_name, 'Classifier', 'Unsuported file path/type'))
            return 1

    def unified_entity_uploader(self, path) -> int:
        """
        Uploads unified entity folder

        Args:
            path: the folder path of a unified entity in the format `Pack/{Pack_Name}/Integration/{Integration_Name}`

        Returns:
            status code
        """
        if get_parent_directory_name(path) not in UNIFIED_ENTITIES_DIR:
            return 1
        yml_files = []
        for file in glob.glob(f"{path}/*.yml"):
            if not file.endswith('_unified.yml'):
                yml_files.append(file)
        if len(yml_files) > 1:
            self.failed_uploaded_files.append((path, "Entity Folder",
                                               "The folder contains more than one `.yml` file "
                                               "(not including `_unified.yml`)"))
            return 1
        if not yml_files:
            self.failed_uploaded_files.append((path, "Entity Folder", "The folder does not contain a .yml file"))
            return 1
        return self.file_uploader(yml_files[0])

    def entity_dir_uploader(self, path: str) -> int:
        """
        Uploads an entity path directory
        Args:
            path: an entity path in the following format `Packs/{Pack_Name}/{Entity_Type}`

        Returns:
            The status code of the operation.

        """
        status_code = 0
        dir_name = os.path.basename(path.rstrip('/'))
        if dir_name in [INTEGRATIONS_DIR, SCRIPTS_DIR]:
            for entity_folder in glob.glob(f"{path}/*/"):
                status_code = self.unified_entity_uploader(entity_folder) or status_code
        elif dir_name in CONTENT_ENTITIES_DIRS:
            # upload json or yml files. Other files such as `.md`, `.png` should be ignored
            for file in glob.glob(f"{path}/*.yml"):
                status_code = status_code or self.file_uploader(file)
            for file in glob.glob(f"{path}/*.json"):
                status_code = self.file_uploader(file) or status_code
            return status_code
        return 1

    def pack_uploader(self, path: str) -> int:
        status_code = 0
        for entity_folder in glob.glob(f"{path}/*/"):
            if os.path.basename(entity_folder.rstrip('/')) in CONTENT_ENTITIES_DIRS:
                status_code = self.entity_dir_uploader(entity_folder) or status_code
        return status_code


def parse_error_response(error: ApiException, file_type: str, file_name: str):
    """
    Parses error message from exception raised in call to client to upload a file

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
    return message


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
        print_color(tabulate(failed_uploaded_files, headers=['NAME', 'TYPE', 'ERROR'],
                             tablefmt="fancy_grid") + '\n', LOG_COLORS.RED)
