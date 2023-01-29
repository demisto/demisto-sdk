import ast
import glob
import logging
import os
from typing import List, Tuple, Union

import click
import demisto_client
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version
from tabulate import tabulate

from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR,
    CONTENT_ENTITIES_DIRS,
    DASHBOARDS_DIR,
    ENV_DEMISTO_SDK_MARKETPLACE,
    INCIDENT_FIELDS_DIR,
    INCIDENT_TYPES_DIR,
    INDICATOR_FIELDS_DIR,
    INDICATOR_TYPES_DIR,
    INTEGRATIONS_DIR,
    JOBS_DIR,
    LAYOUTS_DIR,
    LISTS_DIR,
    PLAYBOOKS_DIR,
    REPORTS_DIR,
    SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR,
    WIDGETS_DIR,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content.errors import ContentFactoryError
from demisto_sdk.commands.common.content.objects.abstract_objects import (
    JSONObject,
    YAMLObject,
)
from demisto_sdk.commands.common.content.objects.pack_objects.pack import Pack
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import (
    find_type,
    get_child_directories,
    get_demisto_version,
    get_file,
    get_parent_directory_name,
    print_v,
)

json = JSON_Handler()


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
    FileType.LISTS,
    FileType.JOB,
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
    LISTS_DIR,
    JOBS_DIR,
    DASHBOARDS_DIR,
    REPORTS_DIR,
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

    def __init__(
        self,
        input: str,
        insecure: bool = False,
        verbose: bool = False,
        pack_names: list = None,
        skip_validation: bool = False,
        detached_files: bool = False,
        reattach: bool = False,
        override_existing: bool = False,
    ):
        self.path = input
        self.log_verbose = verbose
        verify = (
            (not insecure) if insecure else None
        )  # set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        self.client = demisto_client.configure(verify_ssl=verify)
        self.successfully_uploaded_files: List[Tuple[str, str]] = []
        self.failed_uploaded_files: List[Tuple[str, str, str]] = []
        self.unuploaded_due_to_version: List[
            Tuple[str, str, Version, Version, Version]
        ] = []
        self.demisto_version = get_demisto_version(self.client)
        self.pack_names = pack_names
        self.skip_upload_packs_validation = skip_validation
        self.is_files_to_detached = detached_files
        self.reattach_files = reattach
        self.override_existing = override_existing

    def upload(self):
        """Upload the pack / directory / file to the remote Cortex XSOAR instance."""
        if self.demisto_version == "0":
            click.secho(
                "Could not connect to XSOAR server. Try checking your connection configurations.",
                fg="bright_red",
            )
            return ERROR_RETURN_CODE

        status_code = SUCCESS_RETURN_CODE

        if self.is_files_to_detached:
            item_detacher = ItemDetacher(client=self.client)
            list_detach_items_ids: list = item_detacher.detach_item_manager(
                upload_file=True
            )

            if self.reattach_files:
                item_reattacher = ItemReattacher(client=self.client)
                item_reattacher.reattach_item_manager(
                    detached_files_ids=list_detach_items_ids
                )

            if not self.path:
                return SUCCESS_RETURN_CODE
        host = self.client.api_client.configuration.host
        click.secho(f"Using {host=}")
        click.secho(f"Uploading {self.path} ...")
        if self.path is None or not os.path.exists(self.path):
            click.secho(
                f"Error: Given input path: {self.path} does not exist", fg="bright_red"
            )
            return ERROR_RETURN_CODE

        # uploading a pack zip
        elif self.path.endswith(".zip"):
            status_code = self.zipped_pack_uploader(
                path=self.path, skip_validation=self.skip_upload_packs_validation
            )

        # Uploading a file
        elif os.path.isfile(self.path):
            status_code = self.file_uploader(self.path) or status_code

        # Uploading an entity directory
        elif os.path.isdir(self.path):
            parent_dir_name = get_parent_directory_name(self.path)
            if parent_dir_name in UNIFIED_ENTITIES_DIR:
                status_code = self.unified_entity_uploader(self.path) or status_code
            elif os.path.basename(self.path.rstrip("/")) in CONTENT_ENTITIES_DIRS:
                status_code = self.entity_dir_uploader(self.path) or status_code
            else:
                status_code = self.pack_uploader(self.path) or status_code

        if status_code == ABORTED_RETURN_CODE:
            return status_code

        if (
            not self.successfully_uploaded_files
            and not self.failed_uploaded_files
            and not self.unuploaded_due_to_version
        ):
            # if not uploaded any file
            click.secho(
                f"\nError: Given input path: {self.path} is not uploadable. "
                f"Input path should point to one of the following:\n"
                f"  1. Pack\n"
                f"  2. A content entity directory that is inside a pack. For example: an Integrations directory or "
                f"a Layouts directory\n"
                f"  3. Valid file that can be imported to Cortex XSOAR manually. "
                f"For example a playbook: helloWorld.yml",
                fg="bright_red",
            )
            return ERROR_RETURN_CODE

        print_summary(
            self.successfully_uploaded_files,
            self.unuploaded_due_to_version,
            self.failed_uploaded_files,
        )
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
            message = (
                f"Cannot upload {path} as the file type is not supported for upload."
            )
            if self.log_verbose:
                click.secho(message, fg="bright_red")
            self.failed_uploaded_files.append((file_name, "Unknown", message))
            return ERROR_RETURN_CODE

        file_name = upload_object.path.name  # type: ignore

        entity_type = find_type(str(upload_object.path))
        if entity_type in UPLOAD_SUPPORTED_ENTITIES:
            if upload_object.from_version <= self.demisto_version <= upload_object.to_version:  # type: ignore
                try:
                    result = upload_object.upload(self.client)  # type: ignore
                    if self.log_verbose:
                        if hasattr(result, "to_str"):
                            print_v(f"Result:\n{result.to_str()}", self.log_verbose)
                        else:
                            print_v(f"Result:\n{result}", self.log_verbose)
                        click.secho(
                            f"Uploaded {entity_type} - '{os.path.basename(path)}': successfully",
                            fg="green",
                        )
                    self.successfully_uploaded_files.append(
                        (file_name, entity_type.value)
                    )
                    return SUCCESS_RETURN_CODE
                except Exception as err:
                    message = parse_error_response(
                        err, entity_type, file_name, self.log_verbose
                    )
                    self.failed_uploaded_files.append(
                        (file_name, entity_type.value, message)
                    )
                    return ERROR_RETURN_CODE
            else:
                if self.log_verbose:
                    click.secho(
                        f"Input path {path} is not uploading due to version mismatch.\n"
                        f"XSOAR version is: {self.demisto_version} while the file's version is "
                        f"{upload_object.from_version} - {upload_object.to_version}",
                        fg="bright_red",
                    )
                self.unuploaded_due_to_version.append(
                    (
                        file_name,
                        entity_type.value,
                        self.demisto_version,  # type: ignore
                        upload_object.from_version,
                        upload_object.to_version,
                    )
                )
                return ERROR_RETURN_CODE
        else:
            if self.log_verbose:
                click.secho(
                    f"\nError: Given input path: {path} is not uploadable. "
                    f"Input path should point to one of the following:\n"
                    f"  1. Pack\n"
                    f"  2. A content entity directory that is inside a pack. For example: an Integrations directory or "
                    f"a Layouts directory\n"
                    f"  3. Valid file that can be imported to Cortex XSOAR manually. "
                    f"For example a playbook: helloWorld.yml",
                    fg="bright_red",
                )
            self.failed_uploaded_files.append(
                (file_name, entity_type.value, "Unsuported file path/type")
            )
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
            if not file.endswith("_unified.yml"):
                yml_files.append(file)
        if len(yml_files) > 1:
            self.failed_uploaded_files.append(
                (
                    path,
                    "Entity Folder",
                    "The folder contains more than one `.yml` file "
                    "(not including `_unified.yml`)",
                )
            )
            return ERROR_RETURN_CODE
        if not yml_files:
            self.failed_uploaded_files.append(
                (path, "Entity Folder", "The folder does not contain a `.yml` file")
            )
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
        dir_name = os.path.basename(path.rstrip("/"))
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
        sorted_directories = sort_directories_based_on_dependencies(
            get_child_directories(path)
        )
        for entity_folder in sorted_directories:
            if os.path.basename(entity_folder.rstrip("/")) in CONTENT_ENTITIES_DIRS:
                status_code = self.entity_dir_uploader(entity_folder) or status_code
        return status_code

    def zipped_pack_uploader(self, path: str, skip_validation: bool) -> int:

        zipped_pack = Pack(path)

        try:
            logger = logging.getLogger("demisto-sdk")

            if not self.pack_names:
                self.pack_names = [zipped_pack.path.stem]

            if self.notify_user_should_override_packs():
                zipped_pack.upload(logger, self.client, skip_validation)
                self.successfully_uploaded_files.extend(
                    [(pack_name, FileType.PACK.value) for pack_name in self.pack_names]
                )
                return SUCCESS_RETURN_CODE

            return ABORTED_RETURN_CODE

        except (Exception, KeyboardInterrupt) as err:
            file_name = zipped_pack.path.name  # type: ignore
            message = parse_error_response(
                err, FileType.PACK.value, file_name, self.log_verbose
            )
            self.failed_uploaded_files.append((file_name, FileType.PACK.value, message))
            return ERROR_RETURN_CODE

    def notify_user_should_override_packs(self):
        """Notify the user about possible overridden packs."""

        response = self.client.generic_request(
            "/contentpacks/metadata/installed", "GET"
        )
        installed_packs = eval(response[0])
        if installed_packs:
            installed_packs = {pack["name"] for pack in installed_packs}
            common_packs = installed_packs & set(self.pack_names)  # type: ignore
            if common_packs:
                pack_names = "\n".join(common_packs)
                marketplace = (
                    os.environ.get(
                        ENV_DEMISTO_SDK_MARKETPLACE, MarketplaceVersions.XSOAR
                    )
                    .lower()
                    .replace(MarketplaceVersions.MarketplaceV2, "XSIAM")
                    .upper()
                )
                click.secho(
                    f"This command will overwrite the following packs:\n{pack_names}.\n"
                    f"Any changes made on {marketplace} will be lost.",
                    fg="bright_red",
                )
                if not self.override_existing:
                    click.secho(
                        "Are you sure you want to continue? Y/[N]", fg="bright_red"
                    )
                    answer = str(input())
                    return answer in ["y", "Y", "yes"]

        return True


def parse_error_response(
    error: ApiException, file_type: str, file_name: str, print_error: bool = False
):
    """
    Parses error message from exception raised in call to client to upload a file

    error (ApiException): The exception which was raised in call in to client
    file_type (str): The file type which was attempted to be uploaded
    file_name (str): The file name which was attempted to be uploaded
    """
    message = error
    if hasattr(error, "reason"):
        if "[SSL: CERTIFICATE_VERIFY_FAILED]" in str(error.reason):
            message = (
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n"
                "Try running the command with --insecure flag."
            )

        elif "Failed to establish a new connection:" in str(error.reason):
            message = (
                "Failed to establish a new connection: Connection refused.\n"
                "Try checking your BASE url configuration."
            )

        elif error.reason in ("Bad Request", "Forbidden"):
            error_body = json.loads(error.body)
            message = error_body.get("error")

            if error_body.get("status") == 403:
                message += "\nTry checking your API key configuration."
    if print_error:
        click.secho(str(f"\nUpload {file_type}: {file_name} failed:"), fg="bright_red")
        click.secho(str(message), fg="bright_red")
    if isinstance(error, KeyboardInterrupt):
        message = "Aborted due to keyboard interrupt."
    return message


def print_summary(
    successfully_uploaded_files, unuploaded_due_to_version, failed_uploaded_files
):
    """Prints uploaded files summary
    Successful uploads grid based on `successfully_uploaded_files` attribute in green color
    Failed uploads grid based on `failed_uploaded_files` attribute in red color
    """
    click.secho("\n\nUPLOAD SUMMARY:")
    if successfully_uploaded_files:
        click.secho("\nSUCCESSFUL UPLOADS:", fg="green")
        click.secho(
            tabulate(
                successfully_uploaded_files,
                headers=["NAME", "TYPE"],
                tablefmt="fancy_grid",
            )
            + "\n",
            fg="green",
        )
    if unuploaded_due_to_version:
        click.secho("\nNOT UPLOADED DUE TO VERSION MISMATCH:", fg="yellow")
        click.secho(
            tabulate(
                unuploaded_due_to_version,
                headers=[
                    "NAME",
                    "TYPE",
                    "XSOAR Version",
                    "FILE_FROM_VERSION",
                    "FILE_TO_VERSION",
                ],
                tablefmt="fancy_grid",
            )
            + "\n",
            fg="yellow",
        )
    if failed_uploaded_files:
        click.secho("\nFAILED UPLOADS:", fg="bright_red")
        click.secho(
            tabulate(
                failed_uploaded_files,
                headers=["NAME", "TYPE", "ERROR"],
                tablefmt="fancy_grid",
            )
            + "\n",
            fg="bright_red",
        )


def sort_directories_based_on_dependencies(dir_list: list) -> list:
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
    dir_list.sort(
        key=lambda item: srt.get(os.path.basename(item))  # type: ignore[arg-type, return-value]
    )
    return dir_list


class ConfigFileParser:
    """Parse configuration file to get a list of custom packs to upload to a remote Cortex XSOAR instance.
    Attributes:
        config_file_path (str): The path of the configuration file.
    """

    def __init__(self, config_file_path: str):
        self.config_file_path = config_file_path

    def parse_file(self):
        config_file_data = self.get_file_data()
        custom_packs_paths = self.get_custom_packs_paths(config_file_data)
        return custom_packs_paths

    def get_file_data(self):
        with open(self.config_file_path) as config_file:
            config_file_data = json.load(config_file)
        return config_file_data

    def get_custom_packs_paths(self, config_file_data):
        custom_packs = config_file_data.get("custom_packs", [])
        custom_packs_paths = ",".join(pack.get("url") for pack in custom_packs)
        return custom_packs_paths


class ItemDetacher:
    def __init__(self, client, file_path: str = "SystemPacks"):
        self.file_path = file_path
        self.client = client

    DETACH_ITEM_TYPE_TO_ENDPOINT: dict = {
        "IncidentTypes": "/incidenttype/detach/:id/",
        "Layouts": "/layout/:id/detach/",
        "Playbooks": "/playbook/detach/:id/",
        "Scripts": "/automation/detach/:id/",
    }

    VALID_FILES_FOR_DETACH = ["Playbooks", "Scripts", "IncidentTypes", "Layouts"]

    def detach_item(self, file_id, file_path):
        endpoint: str = ""
        for file_type, file_endpoint in self.DETACH_ITEM_TYPE_TO_ENDPOINT.items():
            if file_type in file_path:
                endpoint = file_endpoint
                break
        endpoint = endpoint.replace(":id", file_id)

        try:
            self.client.generic_request(endpoint, "POST")
            click.secho(f"\nFile: {file_id} was detached", fg="green")
        except Exception as e:
            raise Exception(f"Exception raised when fetching custom content:\n{e}")

    def extract_items_from_dir(self):
        detach_files_list: list = []

        all_files = glob.glob(f"{self.file_path}/**/*", recursive=True)
        for file_path in all_files:
            if os.path.isfile(file_path) and self.is_valid_file_for_detach(file_path):
                file_type = self.find_item_type_to_detach(file_path)
                file_data = get_file(file_path, file_type)
                file_id = file_data.get("id")
                if file_id:
                    detach_files_list.append(
                        {
                            "file_id": file_id,
                            "file_type": file_type,
                            "file_path": file_path,
                        }
                    )
        return detach_files_list

    def is_valid_file_for_detach(self, file_path: str) -> bool:
        for file in self.VALID_FILES_FOR_DETACH:
            if file in file_path and (
                file_path.endswith("yml") or file_path.endswith("json")
            ):
                return True
        return False

    def find_item_type_to_detach(self, file_path) -> str:
        return "yml" if "Playbooks" in file_path or "Scripts" in file_path else "json"

    def find_item_id_to_detach(self):
        file_type = self.find_item_type_to_detach(self.file_path)
        file_data = get_file(self.file_path, file_type)
        file_id = file_data.get("id")
        return file_id

    def detach_item_manager(self, upload_file: bool = False):
        detach_files_list: list = []
        if os.path.isdir(self.file_path):
            detach_files_list = self.extract_items_from_dir()
            for file in detach_files_list:
                self.detach_item(file.get("file_id"), file_path=file.get("file_path"))
                if upload_file:
                    uploader = Uploader(input=file.get("file_path"))
                    uploader.upload()

        elif os.path.isfile(self.file_path):
            file_id = self.find_item_id_to_detach()
            detach_files_list.append({"file_id": file_id, "file_path": self.file_path})
            self.detach_item(file_id=file_id, file_path=self.file_path)
            if upload_file:
                uploader = Uploader(input=self.file_path)
                uploader.upload()

        detached_items_ids = [file.get("file_id") for file in detach_files_list]
        return detached_items_ids


class ItemReattacher:
    def __init__(self, client, file_path: str = ""):
        self.file_path = file_path
        self.client = client

    REATTACH_ITEM_TYPE_TO_ENDPOINT: dict = {
        "IncidentType": "/incidenttype/attach/:id",
        "Layouts": "/layout/:id/attach",
        "Playbooks": "/playbook/attach/:id",
        "Automations": "/automation/attach/:id",
    }

    def download_all_detach_supported_items(self) -> dict:
        all_detach_supported_items: dict = {}
        yml_req_body = {"query": "system:T"}

        for endpoint in ["/playbook/search", "/automation/search"]:
            res = self.client.generic_request(endpoint, "POST", body=yml_req_body)
            res_result = ast.literal_eval(res[0])
            if "playbook" in endpoint:
                all_detach_supported_items["Playbooks"] = res_result.get("playbooks")
            else:
                all_detach_supported_items["Automations"] = res_result.get("scripts")

        for item_type in ["IncidentType", "Layouts"]:
            endpoint = item_type.lower()
            res = self.client.generic_request(endpoint, "GET")
            all_detach_supported_items[item_type] = ast.literal_eval(res[0])

        return all_detach_supported_items

    def reattach_item(self, item_id, item_type):
        endpoint: str = self.REATTACH_ITEM_TYPE_TO_ENDPOINT[item_type]
        endpoint = endpoint.replace(":id", item_id)
        try:
            self.client.generic_request(endpoint, "POST")
            click.secho(f"\n{item_type}: {item_id} was reattached", fg="green")
        except Exception as e:
            raise Exception(f"Exception raised when fetching custom content:\n{e}")

    def reattach_item_manager(self, detached_files_ids=None):
        if not self.file_path and detached_files_ids:
            all_files: dict = self.download_all_detach_supported_items()
            for item_type, item_list in all_files.items():
                for item in item_list:
                    if (
                        not item.get("detached", "")
                        or item.get("detached", "") == "false"
                    ):
                        continue
                    item_id = item.get("id")
                    if item_id and item_id not in detached_files_ids:
                        self.reattach_item(item_id, item_type)
