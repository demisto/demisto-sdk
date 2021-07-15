import glob
import json
import logging
import os
from typing import List, Tuple, Union

import click
import demisto_client
from demisto_client.demisto_api.rest import ApiException
from demisto_sdk.commands.common.constants import (CLASSIFIERS_DIR,
                                                   CONTENT_ENTITIES_DIRS,
                                                   DASHBOARDS_DIR,
                                                   INCIDENT_FIELDS_DIR,
                                                   INCIDENT_TYPES_DIR,
                                                   INDICATOR_FIELDS_DIR,
                                                   INDICATOR_TYPES_DIR,
                                                   INTEGRATIONS_DIR,
                                                   LAYOUTS_DIR, PACKS_DIR,
                                                   PLAYBOOKS_DIR, REPORTS_DIR,
                                                   SCRIPTS_DIR,
                                                   TEST_PLAYBOOKS_DIR,
                                                   WIDGETS_DIR, FileType)
from demisto_sdk.commands.common.content.errors import ContentFactoryError
from demisto_sdk.commands.common.content.objects.abstract_objects import (
    JSONObject, YAMLObject)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import (find_type,
                                               get_child_directories,
                                               get_demisto_version,
                                               get_parent_directory_name,
                                               print_v)
from packaging.version import Version
from tabulate import tabulate

# These are the class names of the objects in demisto_sdk.commands.common.content.objects
UPLOAD_SUPPORTED_ENTITIES = [
    FileType.INTEGRATION,
    FileType.BETA_INTEGRATION,
    FileType.SCRIPT,
    FileType.TEST_SCRIPT,

    FileType.PLAYBOOK,
    FileType.TEST_PLAYBOOK,

    FileType.OLD_CLASSIFIER,
    FileType.CLASSIFIER,
    FileType.MAPPER,

    FileType.INCIDENT_TYPE,
    FileType.INCIDENT_FIELD,
    FileType.REPUTATION,
    FileType.INDICATOR_FIELD,

    FileType.WIDGET,
    FileType.REPORT,
    FileType.DASHBOARD,
    FileType.LAYOUT,
    FileType.LAYOUTS_CONTAINER,
]


UNIFIED_ENTITIES_DIR = [INTEGRATIONS_DIR, SCRIPTS_DIR]

CONTENT_ENTITY_UPLOAD_ORDER = [
    INTEGRATIONS_DIR,
    SCRIPTS_DIR,
    PLAYBOOKS_DIR,
    TEST_PLAYBOOKS_DIR,
    INCIDENT_TYPES_DIR,
    INCIDENT_FIELDS_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    CLASSIFIERS_DIR,
    WIDGETS_DIR,
    LAYOUTS_DIR,
    DASHBOARDS_DIR,
    REPORTS_DIR
]
SUCCESS_RETURN_CODE = 0
ERROR_RETURN_CODE = 1
ABORTED_RETURN_CODE = 2


class Uploader:
    """Upload a pack specified in self.infile to a remote Cortex XSOAR instance.
        Attributes:
            path (str): The path of a pack / directory / file to upload.
            verbose (bool): Whether to output a detailed response.
            client (DefaultApi): Demisto-SDK client object.
        """

    def __init__(self, input: str, insecure: bool = False, verbose: bool = False, pack_names: list = None):
        self.path = input
        self.log_verbose = verbose
        verify = (not insecure) if insecure else None  # set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        self.client = demisto_client.configure(verify_ssl=verify)
        self.successfully_uploaded_files: List[Tuple[str, str]] = []
        self.failed_uploaded_files: List[Tuple[str, str, str]] = []
        self.unuploaded_due_to_version: List[Tuple[str, str, Version, Version, Version]] = []
        self.demisto_version = get_demisto_version(self.client)
        self.pack_names = pack_names

    def upload(self):
        """Upload the pack / directory / file to the remote Cortex XSOAR instance.
        """
        if self.demisto_version == "0":
            click.secho("Could not connect to XSOAR server. Try checking your connection configurations.",
                        fg="bright_red")
            return ERROR_RETURN_CODE

        status_code = SUCCESS_RETURN_CODE
        click.secho(f"Uploading {self.path} ...")
        if self.path is None or not os.path.exists(self.path):
            click.secho(f'Error: Given input path: {self.path} does not exist', fg='bright_red')
            return ERROR_RETURN_CODE

        # uploading a pack zip
        elif self.path.endswith('.zip'):
            status_code = self.zipped_pack_uploader(path=self.path)

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

        if status_code == ABORTED_RETURN_CODE:
            return status_code

        if not self.successfully_uploaded_files \
                and not self.failed_uploaded_files \
                and not self.unuploaded_due_to_version:
            # if not uploaded any file
            click.secho(
                f'\nError: Given input path: {self.path} is not uploadable. '
                f'Input path should point to one of the following:\n'
                f'  1. Pack\n'
                f'  2. A content entity directory that is inside a pack. For example: an Integrations directory or '
                f'a Layouts directory\n'
                f'  3. Valid file that can be imported to Cortex XSOAR manually. '
                f'For example a playbook: helloWorld.yml',
                fg='bright_red'
            )
            return ERROR_RETURN_CODE

        print_summary(self.successfully_uploaded_files, self.unuploaded_due_to_version, self.failed_uploaded_files)
        return status_code

    def file_uploader(self, path: str) -> int:
        """
        Upload a file.
        Args:
            path: The path of the file to upload. The rest of the parameters are taken from self.

        Returns:

        """
        try:
            upload_object: Union[YAMLObject, JSONObject] = path_to_pack_object(path)
        except ContentFactoryError:
            file_name = os.path.split(path)[-1]
            message = f"Cannot upload {path} as the file type is not supported for upload."
            if self.log_verbose:
                click.secho(message, fg='bright_red')
            self.failed_uploaded_files.append((file_name, "Unknown", message))
            return ERROR_RETURN_CODE

        file_name = upload_object.path.name  # type: ignore

        entity_type = find_type(str(upload_object.path))
        if entity_type in UPLOAD_SUPPORTED_ENTITIES:
            if upload_object.from_version <= self.demisto_version <= upload_object.to_version:  # type: ignore
                try:
                    result = upload_object.upload(self.client)  # type: ignore
                    if self.log_verbose:
                        print_v(f'Result:\n{result.to_str()}', self.log_verbose)
                        click.secho(f'Uploaded {entity_type} - \'{os.path.basename(path)}\': successfully', fg='green')
                    self.successfully_uploaded_files.append((file_name, entity_type.value))
                    return SUCCESS_RETURN_CODE
                except Exception as err:
                    message = parse_error_response(err, entity_type, file_name, self.log_verbose)
                    self.failed_uploaded_files.append((file_name, entity_type.value, message))
                    return ERROR_RETURN_CODE
            else:
                if self.log_verbose:
                    click.secho(f"Input path {path} is not uploading due to version mismatch.\n"
                                f"XSOAR version is: {self.demisto_version} while the file's version is "
                                f"{upload_object.from_version} - {upload_object.to_version}", fg='bright_red')
                self.unuploaded_due_to_version.append((file_name, entity_type.value, self.demisto_version,
                                                       upload_object.from_version, upload_object.to_version))
                return ERROR_RETURN_CODE
        else:
            if self.log_verbose:
                click.secho(
                    f'\nError: Given input path: {path} is not uploadable. '
                    f'Input path should point to one of the following:\n'
                    f'  1. Pack\n'
                    f'  2. A content entity directory that is inside a pack. For example: an Integrations directory or '
                    f'a Layouts directory\n'
                    f'  3. Valid file that can be imported to Cortex XSOAR manually. '
                    f'For example a playbook: helloWorld.yml',
                    fg='bright_red'
                )
            self.failed_uploaded_files.append((file_name, entity_type.value, 'Unsuported file path/type'))
            return ERROR_RETURN_CODE

    def unified_entity_uploader(self, path) -> int:
        """
        Uploads unified entity folder

        Args:
            path: the folder path of a unified entity in the format `Pack/{Pack_Name}/Integration/{Integration_Name}`

        Returns:
            status code
        """
        if get_parent_directory_name(path) not in UNIFIED_ENTITIES_DIR:
            return ERROR_RETURN_CODE
        yml_files = []
        for file in glob.glob(f"{path}/*.yml"):
            if not file.endswith('_unified.yml'):
                yml_files.append(file)
        if len(yml_files) > 1:
            self.failed_uploaded_files.append((path, "Entity Folder",
                                               "The folder contains more than one `.yml` file "
                                               "(not including `_unified.yml`)"))
            return ERROR_RETURN_CODE
        if not yml_files:
            self.failed_uploaded_files.append((path, "Entity Folder", "The folder does not contain a `.yml` file"))
            return ERROR_RETURN_CODE
        return self.file_uploader(yml_files[0])

    def entity_dir_uploader(self, path: str) -> int:
        """
        Uploads an entity path directory
        Args:
            path: an entity path in the following format `Packs/{Pack_Name}/{Entity_Type}`

        Returns:
            The status code of the operation.

        """
        status_code = SUCCESS_RETURN_CODE
        dir_name = os.path.basename(path.rstrip('/'))
        if dir_name in UNIFIED_ENTITIES_DIR:
            for entity_folder in glob.glob(f"{path}/*/"):
                status_code = self.unified_entity_uploader(entity_folder) or status_code
        if dir_name in CONTENT_ENTITIES_DIRS:
            # upload json or yml files. Other files such as `.md`, `.png` should be ignored
            for file in glob.glob(f"{path}/*.yml"):
                status_code = self.file_uploader(file) or status_code
            for file in glob.glob(f"{path}/*.json"):
                status_code = self.file_uploader(file) or status_code
        return status_code

    def pack_uploader(self, path: str) -> int:
        status_code = SUCCESS_RETURN_CODE
        sorted_directories = sort_directories_based_on_dependencies(get_child_directories(path))
        for entity_folder in sorted_directories:
            if os.path.basename(entity_folder.rstrip('/')) in CONTENT_ENTITIES_DIRS:
                status_code = self.entity_dir_uploader(entity_folder) or status_code
        return status_code

    def zipped_pack_uploader(self, path: str) -> int:

        zipped_pack = Pack(path)

        try:
            logger = logging.getLogger('demisto-sdk')

            if not self.pack_names:
                self.pack_names = [zipped_pack.path.stem]

            if self.notify_user_should_override_packs():
                zipped_pack.upload(logger, self.client)
                self.successfully_uploaded_files.extend([(pack_name, FileType.PACK.value) for pack_name in self.pack_names])
                return SUCCESS_RETURN_CODE

            return ABORTED_RETURN_CODE

        except (Exception, KeyboardInterrupt) as err:
            file_name = zipped_pack.path.name  # type: ignore
            message = parse_error_response(err, FileType.PACK.value, file_name, self.log_verbose)
            self.failed_uploaded_files.append((file_name, FileType.PACK.value, message))
            return ERROR_RETURN_CODE

    def notify_user_should_override_packs(self):
        """Notify the user about possible overridden packs"""

        response = self.client.generic_request('/contentpacks/metadata/installed', "GET")
        installed_packs = eval(response[0])
        if installed_packs:
            installed_packs = {pack['name'] for pack in installed_packs}
            common_packs = installed_packs & set(self.pack_names)  # type: ignore
            if common_packs:
                pack_names = '\n'.join(common_packs)
                click.secho(f'This command will overwrite the following packs:\n{pack_names}.\n'
                            'Any changes made on XSOAR will be lost.\n'
                            'Are you sure you want to continue? Y/[N]', fg='bright_red')
                answer = str(input())
                return answer in ['y', 'Y', 'yes']

        return True


def parse_error_response(error: ApiException, file_type: str, file_name: str, print_error: bool = False):
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
    if print_error:
        click.secho(str(f'\nUpload {file_type}: {file_name} failed:'), fg='bright_red')
        click.secho(str(message), fg='bright_red')
    if isinstance(error, KeyboardInterrupt):
        message = 'Aborted due to keyboard interrupt.'
    return message


def print_summary(successfully_uploaded_files, unuploaded_due_to_version, failed_uploaded_files):
    """Prints uploaded files summary
    Successful uploads grid based on `successfully_uploaded_files` attribute in green color
    Failed uploads grid based on `failed_uploaded_files` attribute in red color
    """
    click.secho('\n\nUPLOAD SUMMARY:')
    if successfully_uploaded_files:
        click.secho('\nSUCCESSFUL UPLOADS:', fg='green')
        click.secho(tabulate(successfully_uploaded_files, headers=['NAME', 'TYPE'],
                             tablefmt="fancy_grid") + '\n', fg='green')
    if unuploaded_due_to_version:
        click.secho('\nNOT UPLOADED DUE TO VERSION MISMATCH:', fg='yellow')
        click.secho(tabulate(unuploaded_due_to_version, headers=['NAME', 'TYPE', 'XSOAR Version',
                                                                 'FILE_FROM_VERSION', 'FILE_TO_VERSION'],
                             tablefmt="fancy_grid") + '\n', fg='yellow')
    if failed_uploaded_files:
        click.secho('\nFAILED UPLOADS:', fg='bright_red')
        click.secho(tabulate(failed_uploaded_files, headers=['NAME', 'TYPE', 'ERROR'],
                             tablefmt="fancy_grid") + '\n', fg='bright_red')


def sort_directories_based_on_dependencies(dir_list: List) -> List:
    """
    Sorts given list of directories based on logic order of content entities that depend on each other.
    If a given directory does not appear in the CONTENT_ENTITY_UPLOAD_ORDER list it will be ignored

    Args:
        dir_list (List): List of directories to sort

    Returns:
        List. The sorted list of directories.
    """
    srt = {item: index for index, item in enumerate(CONTENT_ENTITY_UPLOAD_ORDER)}
    dir_list_copy = dir_list.copy()
    for dir_path in dir_list_copy:
        if os.path.basename(dir_path) not in CONTENT_ENTITY_UPLOAD_ORDER:
            dir_list.remove(dir_path)
    dir_list.sort(key=lambda item: srt.get(os.path.basename(item)))
    return dir_list
