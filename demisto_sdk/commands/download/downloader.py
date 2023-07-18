import ast
import os
import re
import shutil
import tarfile
import traceback
from collections import defaultdict
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import mkdtemp
from typing import Dict, List, Optional, Union, DefaultDict

import mergedeep

import demisto_client.demisto_api
from demisto_client.demisto_api.rest import ApiException
from dictor import dictor
from flatten_dict import unflatten
from tabulate import tabulate
from urllib3.exceptions import MaxRetryError

from demisto_sdk.commands.common.constants import (
    AUTOMATION,
    CONTENT_ENTITIES_DIRS,
    CONTENT_FILE_ENDINGS,
    DELETED_JSON_FIELDS_BY_DEMISTO,
    DELETED_YML_FIELDS_BY_DEMISTO,
    ENTITY_NAME_SEPARATORS,
    ENTITY_TYPE_TO_DIR,
    FILE_EXIST_REASON,
    FILE_NOT_IN_CC_REASON,
    INCIDENT,
    INTEGRATION,
    INTEGRATIONS_DIR,
    LAYOUT,
    PLAYBOOK,
    PLAYBOOKS_DIR,
    SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR,
    UUID_REGEX,
    SCRIPT,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_child_files,
    get_code_lang,
    get_dict_from_file,
    get_display_name,
    get_entity_id_by_entity_type,
    get_entity_name_by_entity_type,
    get_file,
    get_files_in_dir,
    get_id,
    get_json,
    get_yaml,
    get_yml_paths_in_dir,
    is_sdk_defined_working_offline,
    write_dict,
    create_stringio_object,
    get_file_details,
)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.init.initiator import Initiator
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter

ITEM_TYPE_TO_ENDPOINT: dict = {
    "IncidentType": "/incidenttype",
    "IndicatorType": "/reputation",
    "Field": "/incidentfields",
    "Layout": "/layouts",
    "Playbook": "/playbook/search",
    "Automation": "automation/load/",
    "Classifier": "/classifier/search",
    "Mapper": "/classifier/search",
}

ITEM_TYPE_TO_REQUEST_TYPE = {
    "IncidentType": "GET",
    "IndicatorType": "GET",
    "Field": "GET",
    "Layout": "GET",
    "Playbook": "GET",
    "Automation": "POST",
    "Classifier": "POST",
    "Mapper": "POST",
}

ITEM_TYPE_TO_PREFIX = {
    "IncidentType": ".json",
    "IndicatorType": ".json",
    "Field": ".json",
    "Layout": ".json",
    "Playbook": ".yml",
    "Automation": ".yml",
    "Classifier": ".json",
    "Mapper": ".json",
}


class Downloader:
    """
    Downloader is a class that's designed to download and merge custom content from XSOAR to the content repository.

    Attributes:
        output_pack_path (str): The path of the output pack to download custom content to
        input_files (list): The list of custom content files names to download
        regex (str): Regex Pattern, download all the custom content files that match this regex pattern
        force (bool): Indicates whether to merge existing files or not
        insecure (bool): Indicates whether to use insecure connection or not
        client (Demisto client): The XSOAR client to make API calls
        list_files (bool): Indicates whether to print the list of available custom content files and exit or not
        all_custom_content (bool): Indicates whether to download all available custom content or not
        run_format (bool): Indicates whether to run demisto-sdk format on downloaded files or not
        files_not_downloaded (list): A list of all files didn't succeeded to be downloaded
        pack_content (dict): The pack content that maps the pack
        system (bool): whether to download system items
        item_type (str): The items type to download, use just when downloading system items.
        init (bool): Initialize a new Pack and download the items to it. This will create an empty folder for each supported content item type.
        keep_empty_folders (bool): Whether to keep empty folders when using init.
    """

    def __init__(
        self,
        output: str,
        input: Union[str, List[str]],
        regex: str = "",
        force: bool = False,
        insecure: bool = False,
        list_files: bool = False,
        all_custom_content: bool = False,
        run_format: bool = False,
        system: bool = False,
        item_type: str = "",
        init: bool = False,
        keep_empty_folders: bool = False,
        **kwargs,
    ):
        self.output_pack_path = output
        self.input_files = [input] if isinstance(input, str) else list(input)
        self.regex = regex
        self.force = force
        self.download_system_item = system
        self.system_item_type = item_type
        self.insecure = insecure
        self.list_files = list_files
        self.all_custom_content = all_custom_content
        self.run_format = run_format
        self.client = None
        self.system_content_temp_dir = mkdtemp()
        self.pack_content: Dict[str, list] = {
            entity: list() for entity in CONTENT_ENTITIES_DIRS
        }
        self.init = init
        self.keep_empty_folders = keep_empty_folders
        if is_sdk_defined_working_offline() and self.run_format:
            self.run_format = False
            logger.info(
                "Formatting is not supported when the DEMISTO_SDK_OFFLINE_ENV environment variable is set, Skipping..."
            )

    def download(self) -> int:
        """
        Downloads custom content data from Demisto to the output pack in content repository.
        :return: The exit code
        """
        exit_code: int = self.download_manager()
        self.remove_traces()
        return exit_code

    def download_manager(self) -> int:
        """
        Manages all download command flows
        :return The exit code of each flow
        """
        try:
            if not (self.verify_output_path() and self.verify_flags()):
                return 1

            if self.init:
                self.initialize_output_path()

            if not self.download_system_item or self.list_files:
                # We first parse and load all downloaded custom content, for 2 reasons:
                # - The input files / regex for filtering what content to download use content names and not file names,
                #   so we need to parse all content in order to find the content names that match the input.
                #   (there can be different content types with the same name, so we can't stop after we found a match)
                # - In order to replace UUID IDs with names within the downloaded files, we need to know to which name
                #   each UUID corresponds.
                custom_content_data = self.download_custom_content()
                custom_content_objects = self.parse_custom_content_data(custom_content_data=custom_content_data)

                # If we're in list-files mode, print the list of available files and exit
                if self.list_files:
                    logger.info(f"list-files (-lf) mode detected. Listing available custom content files "
                                f"({len(custom_content_objects)}):")
                    table_str = self.create_custom_content_table(custom_content_objects=custom_content_objects)

                    logger.info(
                        f"Custom content available to download from configured Cortex XSOAR instance:\n\n{table_str}"
                    )
                    return 0

                uuid_mapping = self.create_uuid_to_name_mapping(custom_content_objects=custom_content_objects)

                # Now that we collected all the data we need from all custom content,
                # we can continue the processing only on the files that are actually downloaded.
                filtered_custom_content = self.filter_custom_content(custom_content_objects=custom_content_objects)

                # Replace UUID IDs with names in filtered content (only content we download)
                changed_uuids_count = 0
                for _, file_object in filtered_custom_content.items():
                    if self.replace_uuid_ids(custom_content_object=file_object, uuid_mapping=uuid_mapping):
                        changed_uuids_count += 1

                if changed_uuids_count > 0:
                    logger.debug(f"Replaced UUID IDs in {changed_uuids_count} custom content items.")

            if self.download_system_item:
                if not self.fetch_system_content():
                    return 1

            existing_pack_data = self.build_existing_pack_structure(existing_pack_path=Path(self.output_pack_path))

            if self.download_system_item:
                self.build_system_content()

            # self.update_pack_hierarchy()  # TODO: Handle this within 'write_files_into_output_path'
            result = self.write_files_into_output_path(downloaded_content_objects=filtered_custom_content,  # TODO: Handle system content as well
                                                       existing_pack_structure=existing_pack_data)

            return 0 if result else 1  # Return 0 if download was successful, 1 otherwise

        except Exception as e:
            logger.error(f"Error occurred during download process: {e}")
            logger.error(traceback.format_exc())  # Print traceback in debug only
            return 1

    def verify_flags(self) -> bool:
        """
        Verifies that the flags configuration given by the user is correct
        :return: The verification result
        """
        if not self.list_files:
            if not self.output_pack_path:
                logger.error("Error: Missing required parameter '-o' / '--output'.")
                return False

            if not any((self.input_files, self.all_custom_content, self.regex)):
                logger.error("Error: No input parameter has been provided "
                             "('-i' / '--input', '-r' / '--regex', '-a' / '--all.")
                return False

        if self.download_system_item and not self.system_item_type:
            logger.error(
                "Error: Missing required parameter for downloading system items: '-it' / '--item-type'."
            )
            return False

        return True

    def filter_custom_content(self, custom_content_objects: dict[str, dict]) -> dict[str, dict]:
        """
        Filter custom content data to include only relevant files for the current download command.
        The function also updates self.input_file with names of content matching the filter.

        Args:
            custom_content_objects (dict[str, dict]): A dictionary mapping custom content names
                to their corresponding objects to filter.

        Returns:
            dict[str, dict]: A new custom content objects dict with filtered items.
        """
        file_name_to_content_name_map = {
            key: value["name"] for key, value in custom_content_objects.items()
        }
        filtered_custom_content_objects: dict[str, dict] = {}

        if self.all_custom_content:  # If all custom content should be downloaded
            logger.debug("Filtering process has been skipped as all custom content should be downloaded.")
            for file_name, content_item_data in custom_content_objects.items():
                content_item_name = file_name_to_content_name_map[file_name]
                self.input_files.append(content_item_name)
                filtered_custom_content_objects[content_item_name] = content_item_data

            return filtered_custom_content_objects

        original_count = len(custom_content_objects)
        logger.debug(f"Filtering custom content data ({original_count})...")

        for file_name in custom_content_objects:
            content_item_name = file_name_to_content_name_map[file_name]

            # Filter according to regex filter and input files (whichever is provided)
            if (self.regex and re.match(self.regex, content_item_name)) or (content_item_name in self.input_files):
                self.input_files.append(content_item_name)
                filtered_custom_content_objects[content_item_name] = custom_content_objects[file_name]

        # Filter out content written in JavaScript since it is not support
        # TODO: Check if we actually need this (why don't we allow downloading JS content?) and remove if not.
        for filtered_custom_content_name, filtered_custom_content_object in filtered_custom_content_objects.items():
            code_language: str = filtered_custom_content_object.get("code_lang")
            content_type: str = filtered_custom_content_object["type"]

            if content_type in ("integration", "script") and code_language in ("javascript", None):
                content_name = filtered_custom_content_object["name"]
                logger.warning(f"Content item '{content_name}' is written in JavaScript which isn't supported, "
                               f"and will be skipped.")
                self.input_files.remove(content_name)
                del filtered_custom_content_objects[filtered_custom_content_name]

        logger.info(f"Filtering process completed ({len(filtered_custom_content_objects)}/{original_count}).")

        return filtered_custom_content_objects

    def handle_api_exception(self, e):
        if e.status == 401:
            logger.error(
                "\nAuthentication Error: please verify that the appropriate environment variables "
                "(either DEMISTO_USERNAME and DEMISTO_PASSWORD, or just DEMISTO_API_KEY) are properly configured.\n"
            )
        logger.error(f"Exception raised while fetching custom content:\nStatus: {e}")

    def handle_max_retry_error(self, e):
        logger.error(
            "\nVerify that the environment variable DEMISTO_BASE_URL is configured properly.\n"
        )
        logger.error(f"Exception raised while fetching custom content:\n{e}")

    def create_uuid_to_name_mapping(self, custom_content_objects: dict[str, dict]) -> dict[str, str]:
        """
        Find and map UUID IDs of custom content to their names.

        Args:
            custom_content_objects (dict[str, dict]):
                A dictionary mapping custom content names to their corresponding objects.

        Returns:
            dict[str, str]: A dictionary mapping UUID IDs to corresponding names of custom content.
        """
        logger.info("Creating ID mapping for custom content...")
        mapping: dict[str, str] = {}

        for _, content_object in custom_content_objects.items():
            if content_object["file_name"].startswith(
                (PLAYBOOK, AUTOMATION, SCRIPT, INTEGRATION, LAYOUT, INCIDENT)
            ):
                content_item_id = content_object["id"]
                pass

                if content_item_id and re.match(UUID_REGEX, content_item_id):
                    mapping[content_item_id] = content_object["name"]

        logger.info("Custom content IDs mapping created successfully.")
        return mapping

    def download_custom_content(self) -> dict[str, StringIO]:
        """
        Download custom content bundle using server's API,
        and create a StringIO object containing file data for each file within it.

        Returns:
            dict[str, StringIO]: A dictionary mapping custom content's file names to file objects.
        """
        # Set to 'verify' to None so that 'demisto_client' will use the environment variable 'DEMISTO_VERIFY_SSL'.
        verify = not self.insecure if self.insecure else None
        logger.info("Fetching custom content bundle from server...")

        try:
            self.client = demisto_client.configure(verify_ssl=verify)
            api_response, _, _ = demisto_client.generic_request_func(
                self.client, "/content/bundle", "GET", response_type="object"
            )

        except ApiException as e:
            self.handle_api_exception(e)
            raise

        except MaxRetryError as e:
            self.handle_max_retry_error(e)
            raise

        logger.info("Custom content bundle fetched successfully.")
        logger.debug(f"Downloaded content bundle size (bytes): {len(api_response)}")

        loaded_files: dict[str, StringIO] = {}

        with tarfile.open(fileobj=BytesIO(api_response), mode="r") as tar:
            tar_members = tar.getmembers()
            logger.debug(f"Custom content bundle contains {len(tar_members)} items.")

            logger.debug(f"Loading custom content bundle to memory...")
            for file in tar_members:
                file_name = file.name.lstrip("/")
                file_data = create_stringio_object(tar.extractfile(file).read())
                loaded_files[file_name] = file_data

        logger.debug(f"Custom content bundle loaded to memory successfully.")
        return loaded_files

    def replace_uuid_ids(self, custom_content_object: dict, uuid_mapping: dict[str, str]) -> bool:
        """
        Find and replace UUID IDs of custom content items with their names.
        The method first creates a mapping of a UUID to a name, and then replaces all UUIDs using this mapping.

        Args:
            custom_content_object (dict): A single custom content object to update UUIDs in.
            uuid_mapping (dict[str, str]): A dictionary mapping UUID IDs to corresponding names of custom content.

        Returns:
            bool: True if the object was updated, False otherwise.
        """
        file = custom_content_object["file"]
        content_item_file_str = file.getvalue()

        uuid_matches = re.findall(UUID_REGEX, content_item_file_str)
        # TODO: Check if looping over all dict keys (recursively) is more efficient than dumping to string and then search that using a RegEx.
        # If we do run recursively, consider how we will want to update the StringIO object (if we need it at all?)

        if uuid_matches:
            for uuid in set(uuid_matches).intersection(uuid_mapping):
                logger.debug(f"Replacing UUID '{uuid}' with '{uuid_mapping[uuid]}' in "
                             f"'{custom_content_object['name']}'")
                content_item_file_str = content_item_file_str.replace(uuid, uuid_mapping[uuid])

            # Update ID, if it's a UUID
            if custom_content_object["id"] in uuid_mapping:
                custom_content_object["id"] = uuid_mapping[custom_content_object["id"]]

            # Update custom content object
            file.seek(0)
            file.write(content_item_file_str)
            loaded_file_data = get_file_details(content_item_file_str,
                                                full_file_path=custom_content_object["file_name"])
            custom_content_object["data"] = loaded_file_data

            return True

        return False

    def build_req_params(self) -> tuple[str, str, dict]:
        endpoint = ITEM_TYPE_TO_ENDPOINT[self.system_item_type]
        req_type = ITEM_TYPE_TO_REQUEST_TYPE[self.system_item_type]
        verify = (
            (not self.insecure) if self.insecure else None
        )  # set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        self.client = demisto_client.configure(verify_ssl=verify)

        req_body: dict = {}
        if self.system_item_type in ["Playbook", "Classifier", "Mapper"]:
            filter_by_names = " or ".join(self.input_files)
            req_body = {"query": f"name:{filter_by_names}"}

        return endpoint, req_type, req_body

    def get_system_automation(self, req_type: str) -> list:
        automation_list: list = []
        logger.info("Fetching system automations data...")

        for script in self.input_files:
            endpoint = f"automation/load/{script}"
            api_response = demisto_client.generic_request_func(
                self.client, endpoint, req_type
            )
            automation_list.append(ast.literal_eval(api_response[0]))

        logger.debug(f"'{len(automation_list)}' system automations were downloaded successfully.")
        return automation_list

    def get_system_playbook(self, req_type: str) -> list:
        playbook_list: list = []
        logger.info("Fetching system playbooks data...")

        for playbook in self.input_files:
            endpoint = f"/playbook/{playbook}/yaml"
            try:
                api_response = demisto_client.generic_request_func(
                    self.client, endpoint, req_type, response_type="object"
                )
            except ApiException as err:
                # handling in case the id and name are not the same,
                # trying to get the id by the name through a different api call
                logger.debug(f"API call using playbook's name failed:\n{err}\n"
                             f"Attempting to fetch and use playbook's id...")

                if playbook_id := self.get_playbook_id_by_playbook_name(playbook):
                    logger.debug(f"Successfully fetched playbook's id - '{playbook_id}'\n"
                                 f"Attempting to fetch playbook's YAML file using the ID.")

                    endpoint = f"/playbook/{playbook_id}/yaml"
                    api_response = demisto_client.generic_request_func(
                        self.client, endpoint, req_type, response_type="object"
                    )
                else:
                    raise err
            playbook_list.append(yaml.load(api_response[0].decode()))

        logger.debug(f"'{len(playbook_list)}' system playbooks were downloaded successfully.")
        return playbook_list

    def arrange_response(self, system_items_list):
        if self.system_item_type in ["Classifier", "Mapper"]:
            system_items_list = system_items_list.get("classifiers")

        return system_items_list

    def build_file_name(self, item) -> str:
        item_name: str = item.get("name") or item.get("id")
        return (
            item_name.replace("/", " ").replace(" ", "_")
            + ITEM_TYPE_TO_PREFIX[self.system_item_type]
        )

    def fetch_system_content(self) -> bool:
        """
        Fetch system content from XSOAR into a temporary dir.
        :return: True if fetched successfully, False otherwise
        """
        try:
            endpoint, req_type, req_body = self.build_req_params()

            if self.system_item_type == "Automation":
                system_items_list = self.get_system_automation(req_type)

            elif self.system_item_type == "Playbook":
                system_items_list = self.get_system_playbook(req_type)

            else:
                logger.info(f"Fetching system {self.system_item_type.lower()} data from server...")
                api_response = demisto_client.generic_request_func(
                    self.client, endpoint, req_type, body=req_body
                )
                system_items_list = ast.literal_eval(api_response[0])
                logger.info(
                    f"Fetched {len(system_items_list)} system {self.system_item_type.lower()} items from server."
                )

            system_items_list = self.arrange_response(system_items_list)

            for item in system_items_list:  # type: ignore
                file_name = self.build_file_name(item)
                file_path = Path(self.system_content_temp_dir) / file_name
                write_dict(file_path, data=item)

            return True

        except ApiException as e:
            self.handle_api_exception(e)
            return False
        except MaxRetryError as e:
            self.handle_max_retry_error(e)
            return False
        except Exception as e:
            logger.info(f"Exception raised when fetching system content:\n{e}")
            return False

    def parse_custom_content_data(self, custom_content_data: dict[str, StringIO]) -> dict[str, dict]:
        """
        Converts a mapping of file names to raw file data (StringIO),
        into a mapping of file names to custom content objects (parsed & loaded data)

        Note:
            Custom content items with an empty 'type' key are not supported and will be omitted.

        Args:
            custom_content_data (dict[str, StringIO]): A dictionary mapping file names to file data.

        Returns:
            dict[str, dict]: A dictionary mapping content item's file names, to dictionaries containing metadata
                and content of the item.
        """
        logger.info("Parsing downloaded custom content data into objects...")
        custom_content_objects: dict[str, dict] = {}

        for file_name, file_data in custom_content_data.items():
            try:
                logger.debug(f"Parsing '{file_name}'...")
                custom_content_object: Dict = self.create_content_item_object(
                    file_name=file_name, file_data=file_data
                )

                if custom_content_object.get("type"):  # TODO: currently, this results in `list-` items to be skipped
                    custom_content_objects[file_name] = custom_content_object

                else:
                    logger.warning(f"Content type of '{file_name}' could not be detected. Skipping...")

            # Skip custom_content_objects with an invalid format
            except Exception as e:
                # We fail the whole download process, since we might miss UUIDs to replace
                #  TODO: Check if we want to replace this behavior and just skip the file
                logger.error(f"Error while parsing '{file_name}': {e}")
                raise

        logger.info(f"Successfully parsed '{len(custom_content_objects)}' custom content objects.")
        return custom_content_objects

    def get_existing_content_items_objects(self) -> List[dict]:
        """
        Creates a list of objects representing existing custom content that already exists in target output path.
        """
        system_content_file_paths: list = get_child_files(self.system_content_temp_dir)
        system_content_objects: List = list()
        for file_path in system_content_file_paths:
            try:
                system_content_object: Dict = self.create_content_item_object(
                    file_path
                )
                system_content_objects.append(system_content_object)
            # Do not add file to custom_content_objects if it has an invalid format
            except ValueError as e:
                logger.error(f"Error while loading '{file_path}': {e}\nSkipping...")
        return system_content_objects

    def create_custom_content_table(self, custom_content_objects: dict[str, dict]) -> str:
        """
        Return a printable list of all custom content that's available to download from the configured XSOAR instance.

        Args:
            custom_content_objects (dict[str, dict]): A dictionary mapping custom content's file names to objects.

        Returns:
            str: A printable list of all custom content that's available to download from the configured XSOAR instance.
        """
        tabulate_data: list[list[str]] = []

        for file_name, file_object in custom_content_objects.items():
            if item_name := file_object.get("name"):
                tabulate_data.append([item_name, file_object["type"]])

        return tabulate(tabulate_data, headers=["CONTENT NAME", "CONTENT TYPE"])

    def initialize_output_path(self) -> None:
        """Initialize output path with pack structure."""
        logger.info("Initiating pack structure...")
        root_folder = Path(self.output_pack_path)
        if root_folder.name != "Packs":
            root_folder = root_folder / "Packs"
            try:
                root_folder.mkdir(exist_ok=True)
            except FileNotFoundError as e:
                e.filename = str(Path(e.filename).parent)
                raise
        initiator = Initiator(str(root_folder))
        initiator.init()
        self.output_pack_path = initiator.full_output_path

        if not self.keep_empty_folders:
            self.remove_empty_folders()

        logger.info(f"Initialized pack structure at '{self.output_pack_path}'.")

    def remove_empty_folders(self) -> None:
        """
        Removes empty folders from the output pack path
        :return: None
        """
        pack_folder = Path(self.output_pack_path)
        for folder_path in pack_folder.glob("*"):
            if folder_path.is_dir() and not any(folder_path.iterdir()):
                folder_path.rmdir()

    def verify_output_path(self) -> bool:
        """
        Assure that the output path entered by the user is inside a "Packs" folder.

        Returns:
            bool: True if the output path is valid, False otherwise.
        """
        output_pack_path = Path(self.output_pack_path)

        if not output_pack_path.is_dir():
            logger.error(
                f"Error: Path '{output_pack_path.absolute()}' does not exist, or isn't a directory."
            )

        elif not output_pack_path.parent.name == "Packs":
            logger.error(
                f"Error: Path '{output_pack_path.absolute()}' is invalid.\n"
                f"The provided output path for the download must be inside a 'Packs' folder. e.g., 'Packs/MyPack'."
            )

        # All validations passed
        else:
            return True

        return False

    def build_existing_pack_structure(self, existing_pack_path: Path) -> dict[str, dict[str, list[dict]]]:
        """
        Create a pack structure from the content in the existing output path.
        Used later to determine which files already exist in the output path (by their content name, not file name).

        Args:
            existing_pack_path (Path): The path of the existing pack to parse.

        Returns:
            dict[str, dict[str, list[dict]]]: A dictionary representing the pack structure.

        Example return structure:
        {
            "Integrations":
                "MyIntegration":
                    [
                        {
                            "name": "MyIntegration",
                            "id": "MyIntegration",
                            "path": "Packs/TestPack/Integrations/MyIntegration/MyIntegration.yml",
                            "file_extension": "yml"
                        },
                        {
                            "name": "MyIntegration",
                            "id": "MyIntegration",
                            "path": "Packs/TestPack/Integrations/MyIntegration/MyIntegration.py",
                            "file_extension": "py"
                        },
                        ... (more files, like README and description)
                    ]
        """
        output_pack_path = Path(existing_pack_path)
        pack_structure: DefaultDict[str, dict[str, list]] = defaultdict(dict)

        for content_entity_path in output_pack_path.iterdir():
            if content_entity_path.is_dir():
                directory_name = content_entity_path.name

                if directory_name in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                    # If entity is of type integration/script it will have dirs, otherwise files
                    entity_instances_paths = [p for p in content_entity_path.iterdir() if p.is_dir()]
                else:
                    entity_instances_paths = [p for p in content_entity_path.iterdir() if p.is_file()]

                for entity_instance_path in entity_instances_paths:
                    content_data = self.build_pack_content_object(
                        content_entity=directory_name,
                        entity_instance_path=entity_instance_path
                    )

                    if content_data is not None:
                        content_name, content_object = content_data
                        pack_structure[directory_name][content_name] = content_object

        return dict(pack_structure)

    def build_pack_content_object(
        self, content_entity: str, entity_instance_path: Path
    ) -> tuple[str, list[dict]] | None:
        """
        Build an object representing a single content items that already exists in the output pack path.

        Args:
            content_entity (str): The content entity, for example Integrations.
            entity_instance_path (Path): The path to the content item.

        Returns:
            tuple[str, list[dict] | None: A tuple, containing the content item's name (str),
             and a list of objects representing files (for example YAML & Python) under the content item (list[dict]).
             None if the content item could not be parsed.
        """
        # If the entity_instance_path is a file then get_files_in_dir will return the list: [entity_instance_path]
        file_paths: list = get_files_in_dir(
            str(entity_instance_path), CONTENT_FILE_ENDINGS, recursive=False
        )
        # If it's integration/script, all files under it should have the main details of the yml file,
        # otherwise we'll use the file's details.
        content_item_id, content_item_name = self.get_main_file_details(
            content_entity, entity_instance_path
        )

        # if main file doesn't exist/no entity instance path exist the content object won't be added to the pack content
        if not all((content_item_id, content_item_name, file_paths)):
            logger.debug(f"Existing content item '{content_item_name}' could not be parsed. Skipping...")
            return None

        content_item_files = []

        for file_path in file_paths:
            content_item_files.append(
                {
                    "name": content_item_name,
                    "id": content_item_id,
                    "path": file_path,
                    "file_extension": Path(file_path).suffix,
                }
            )

        return content_item_name, content_item_files

    def get_playbook_id_by_playbook_name(self, playbook_name: str) -> Optional[str]:
        """
        Extract the playbook id by name, calling the api returns an object that cannot be parsed properly,
        and its use is only for extracting the id.

        Args:
            playbook_name (str): The name of a playbook

        Returns:
            Optional[str]: The ID of a playbook
        """
        logger.info(f"Fetching playbook ID using API for '{playbook_name}'...")
        endpoint = "/playbook/search"
        response = demisto_client.generic_request_func(
            self.client,
            endpoint,
            "POST",
            response_type="object",
            body={"query": f"name:{playbook_name}"},
        )
        if not response:
            return None
        if not (playbooks := response[0].get("playbooks")):
            return None
        return playbooks[0]["id"]

    @staticmethod
    def get_main_file_details(content_entity: str, entity_instance_path: Path) -> tuple:
        """
        Returns the details of the "main" file within an entity instance.
        For example: In the HelloWorld integration under Packs/HelloWorld, the main file is the yml file.
        It contains all relevant ids and names for all the files under the HelloWorld integration dir.
        :param content_entity: The content entity, for example Integrations
        :param entity_instance_path: For example: ~/.../content/Packs/TestPack/Integrations/HelloWorld
        :return: The main file id & name
        """
        main_file_data: dict = {}
        main_file_path: str = ""

        # Entities which contain yml files
        if content_entity in (
            INTEGRATIONS_DIR,
            SCRIPTS_DIR,
            PLAYBOOKS_DIR,
            TEST_PLAYBOOKS_DIR,
        ):
            if entity_instance_path.is_dir():
                _, main_file_path = get_yml_paths_in_dir(str(entity_instance_path))
            elif entity_instance_path.is_file():
                main_file_path = str(entity_instance_path)

            if main_file_path:
                main_file_data = get_yaml(main_file_path)

        # Entities which are json files (md files are ignored - changelog/readme)
        else:
            if (
                entity_instance_path.is_file()
                and entity_instance_path.suffix == ".json"
            ):
                main_file_data = get_json(entity_instance_path)

        content_item_id = get_entity_id_by_entity_type(main_file_data, content_entity)
        content_item_name = get_entity_name_by_entity_type(main_file_data, content_entity)

        return content_item_id, content_item_name

    @staticmethod
    def update_file_prefix(file_name: str) -> str:
        """
        Replace 'automation' prefix with 'script' prefix, and remove 'playbook' prefixes.

        Args:
            file_name (str): The file name to update

        Returns:
            str: The updated file name
        """
        return file_name.replace("automation-", "script-").replace("playbook-", "")

    def build_system_content(self) -> None:
        """
        Build a data structure called pack content that holds basic data for each content entity instances downloaded from Demisto.
        For example check out the CUSTOM_CONTENT variable in downloader_test.py
        """
        system_content_objects = self.get_existing_content_items_objects()
        for input_file_name in self.input_files:
            input_file_exist_in_cc: bool = False
            for system_content_object in system_content_objects:
                name = system_content_object.get("name", "N/A")
                id_ = system_content_object.get("id", "N/A")
                if name == input_file_name or id_ == input_file_name:
                    system_content_object["exist_in_pack"] = self.exist_in_pack_content(
                        system_content_object
                    )
                    self.custom_content.append(system_content_object)
                    input_file_exist_in_cc = True
            # If in input files and not in custom content files
            if not input_file_exist_in_cc:
                self.files_not_downloaded.append(
                    [input_file_name, FILE_NOT_IN_CC_REASON]
                )

    def exist_in_pack_content(self, custom_content_object: dict) -> bool:
        """
        Checks if the current custom content object already exists in custom content
        :param custom_content_object: The custom content object
        :return: True if exists, False otherwise
        """
        entity: str = custom_content_object["entity"]
        name = custom_content_object["name"]
        exist_in_pack: bool = False

        for entity_instance_object in self.pack_content[entity]:
            if name in entity_instance_object:
                exist_in_pack = True

        return exist_in_pack

    def create_content_item_object(self, file_name: str, file_data: StringIO) -> dict:
        """
        Convert a single custom content item to a content object.

        Args:
            file_name (str): The file name of the custom content item.
            file_data (StringIO): The file data of the custom content item.

        Returns:
            dict: The custom content object.
        """
        file_extension = file_name.split(".")[-1]
        loaded_file_data: dict
        file_data.seek(0)  # Reset the StringIO cursor to the beginning of the file before parsing
        loaded_file_data = get_file_details(file_content=file_data.getvalue(), full_file_path=file_name)

        if not loaded_file_data:
            raise ValueError(f"Unsupported file extension: {file_extension}")

        if file_type_enum := find_type(path=file_name, _dict=loaded_file_data, file_type=file_extension):
            file_type = file_type_enum.value

        else:
            file_type = ""

        content_name = get_display_name(file_path=file_name, file_data=loaded_file_data)

        file_entity = self.file_type_to_entity(
            content_name=content_name,
            file_type=file_type
        )
        content_id = get_id(loaded_file_data)

        if not content_id:
            logger.warning(f"Could not find content ID for '{file_name}'.")

        custom_content_object: dict = {
            "id": content_id,  # str
            "name": content_name,  # str
            "entity": file_entity,  # str
            "type": file_type,  # str
            "file": file_data,  # StringIO
            "file_name": self.update_file_prefix(file_name),  # str
            "file_extension": file_extension,  # str
            "data": loaded_file_data,  # dict
        }

        if file_code_language := get_code_lang(loaded_file_data, file_entity):
            custom_content_object["code_lang"] = file_code_language

        return custom_content_object

    @staticmethod
    def file_type_to_entity(content_name: str, file_type: str) -> str:
        """
        Given the file type returns the file entity.

        Args:
            content_name (str): Content item's name (not file name)
            file_type (str): Content file's type

        Returns:
            str: File's entity. An empty string if not found.
        """
        if file_type == "playbook":
            if content_name.endswith(
                ("Test", "_test", "_Test", "-test", "-Test")
            ) or content_name.lower().startswith("test"):
                return TEST_PLAYBOOKS_DIR
        return ENTITY_TYPE_TO_DIR.get(file_type, "")

    @staticmethod
    def create_directory_name(content_item_name: str) -> str:
        """
        Creates the directory name for a content item (used for integrations / scripts).
        Example: For a content item named "Hello World Script", "HelloWorldScript" will be returned.

        Args:
            content_item_name (str): Content item's name

        Returns:
            str: The directory name for the content item
        """
        for separator in ENTITY_NAME_SEPARATORS:
            content_item_name = content_item_name.replace(separator, "")
        return content_item_name

    def write_files_into_output_path(self, downloaded_content_objects: dict[str, dict],
                                     existing_pack_structure: dict[str, dict[str, list[dict]]]) -> bool:
        """
        Download the files after processing is done to the output directory.
        For integrations / scripts, YAML extraction is done.
        Content items that already exist in the output pack, will be skipped, unless the '--force' flag is used.
        If it is, the existing and downloaded YAML files will be merged, as some fields are deleted by the server.

        Args:
            downloaded_content_objects (dict[str, dict]): A dictionary of content objects to download.
            existing_pack_structure (dict[str, list]): A dictionary of existing content objects in the output path.

        Returns:
            bool: True if all files were downloaded successfully, False otherwise.
        """
        successful_downloads_count = 0
        existing_files_skipped_count = 0
        failed_downloads_count = 0

        for file_name, content_object in downloaded_content_objects.items():
            content_item_name: str = content_object["name"]
            content_item_entity: str = content_object["entity"]
            content_item_not_skipped = True

            try:
                if content_item_entity in (INTEGRATIONS_DIR, SCRIPTS_DIR):
                    file_downloaded = self.download_unified_content(content_object=content_object,
                                                                    existing_pack_structure=existing_pack_structure,
                                                                    overwrite_existing=self.force)

                else:
                    file_downloaded = self.download_non_unified_content(content_object=content_object,
                                                                        existing_pack_structure=existing_pack_structure,
                                                                        overwrite_existing=self.force)

                # If even one file was skipped, we mark the file as skipped for the logs
                if not file_downloaded:
                    content_item_not_skipped = False

            except Exception as e:
                failed_downloads_count += 1
                logger.error(f"Failed to download content item '{content_item_name}': {e}")
                logger.debug(traceback.format_exc())
                continue

            if content_item_not_skipped:
                successful_downloads_count += 1

            else:
                existing_files_skipped_count += 1

        summary_log = f"{successful_downloads_count} files were downloaded successfully."

        if failed_downloads_count:
            summary_log += f"\n{failed_downloads_count} files failed to download."

        if existing_files_skipped_count:
            summary_log += f"\n{existing_files_skipped_count} files that exist in the output pack were skipped. " \
                           f"Use the '-f' / '--force' flag to override."

        logger.info(summary_log)

        return not failed_downloads_count  # Return True if no downloads failed, False otherwise.

    def download_unified_content(self, content_object: dict,
                                 existing_pack_structure: dict[str, dict[str, list[dict]]],
                                 overwrite_existing: bool = False) -> bool:
        """
        Download unified content items.
        Existing content items will be skipped if 'overwrite_existing' is False.
        A "smart" merge will be done for pre-existing YAML files, adding fields that exist in existing file,
        but were omitted by the server.

        Args:
            content_object (dict): The content object to download
            existing_pack_structure (list[dict]): A list of existing content item files in the output pack.
            overwrite_existing (bool): Whether to overwrite existing files or not.

        Returns:
            bool: True if the content item was downloaded successfully, False otherwise.
        """
        temp_dir: str | None = None
        content_item_name: str = content_object["name"]
        content_item_type: str = content_object["type"]
        content_item_entity: str = content_object["entity"]
        content_directory_name = self.create_directory_name(content_item_name)

        content_item_exists = (  # Content item already exists in output pack
            content_object["name"] in existing_pack_structure[content_item_entity]
        )

        if content_item_exists:
            if not overwrite_existing:  # If file exists, and we don't want to overwrite it, skip it.
                logger.debug(
                    f"Content item '{content_item_name}' already exists in output pack. Skipping..."
                )
                return False

            # If we overwrite existing files, we need to extract the existing files to a temp directory
            # for a "smart" merge.
            temp_dir = mkdtemp()
            output_path = temp_dir

        else:
            output_path = Path(self.output_pack_path, content_item_entity, content_directory_name)
            output_path.mkdir(parents=True, exist_ok=True)  # Create path if it doesn't exist
            output_path = str(output_path)

        extractor = YmlSplitter(
            input=content_object["file_name"],
            output=output_path,
            loaded_data=content_object["data"],
            file_type=content_item_type,
            base_name=content_directory_name,
            no_readme=content_item_exists,  # If the content item exists, no need to download README.md file  # TODO: Change behavior? Why not download README.md in case it was changed?
            no_auto_create_dir=True,
        )
        extractor.extract_to_package_format()
        extracted_file_paths: list[str] = get_child_files(output_path)

        for extracted_file_path in extracted_file_paths:
            if content_item_exists:
                extracted_file_path = Path(extracted_file_path)
                extracted_file_extension = extracted_file_path.suffix

                # Get the file name to search for in the existing output pack
                expected_filename: str = self.get_expected_filename(
                    content_item_name=content_item_name,
                    file_extension=extracted_file_extension,
                )

                # Find extracted file's matching existing file
                corresponding_pack_file_object: dict | None = None

                for file_object in existing_pack_structure[content_item_entity][content_item_name]:
                    if Path(file_object["path"]).name == expected_filename:
                        corresponding_pack_file_object = file_object
                        break

                if corresponding_pack_file_object:
                    corresponding_pack_file_path = corresponding_pack_file_object["path"]

                else:
                    corresponding_pack_file_path: str = os.path.join(
                        self.output_pack_path,
                        content_item_entity,
                        self.create_directory_name(content_item_name),
                        expected_filename,
                    )

                if extracted_file_extension == ".yml":  # "smart" merge is relevant only for YAML files
                    self.update_data(  # Add existing fields that were removed by the server to the new file
                        file_to_update=extracted_file_path,
                        original_file=corresponding_pack_file_path,
                        is_yaml=(extracted_file_extension == ".yml"),
                    )

                shutil.move(src=extracted_file_path, dst=corresponding_pack_file_path)
                final_path = Path(corresponding_pack_file_path)

            # If the file doesn't exist in the pack, the files were extracted to the output path
            else:
                final_path = Path(extracted_file_path)

            if self.run_format and final_path.suffix in (".yml", ".yaml", ".json"):
                format_manager(
                    input=str(final_path),
                    no_validate=False,
                    assume_answer=False,
                )

        try:  # Clean up temp dir
            shutil.rmtree(temp_dir, ignore_errors=True)

        except shutil.Error as e:
            logger.warning(f"Failed to remove temp dir '{temp_dir}': {e}")
            logger.debug(traceback.format_exc())

        logger.debug(f"Content item '{content_item_name}' was successfully downloaded.")
        return True

    def download_non_unified_content(self, content_object: dict,
                                     existing_pack_structure: dict[str, dict[str, list[dict]]],
                                     overwrite_existing: bool = False) -> bool:
        """
        Download non-unified content items.
        Existing content items will be skipped if 'overwrite_existing' is False.
        A "smart" merge will be done for pre-existing YAML files, adding fields that exist in existing file,
        but were omitted by the server.

        Args:
            content_object (dict): The content object to download
            existing_pack_structure (list[dict]): A list of existing content item files in the output pack.
            overwrite_existing (bool): Whether to overwrite existing files or not.

        Returns:
            bool: True if the content item was downloaded successfully, False otherwise.
        """
        content_item_name: str = content_object["name"]
        content_item_entity: str = content_object["entity"]
        content_item_extension: str = content_object["file_extension"]

        content_item_exists = (  # Content item already exists in output pack
            content_object["name"] in existing_pack_structure[content_item_entity]
        )

        # If file exists, and we don't want to overwrite it, skip it.
        if content_item_exists and not overwrite_existing:
            logger.debug(
                f"File '{content_item_name}' already exists in output pack. Skipping..."
            )
            return False

        # Write downloaded file to temp directory
        temp_dir = Path(mkdtemp())

        file_name: str = content_object["file_name"]
        file_path = temp_dir / file_name
        file_data: StringIO = content_object["file"]

        with open(file_path, "w") as f:
            f.write(file_data.getvalue())

        if content_item_exists:
            # The corresponding_pack_object will have a list of length 1 as value if it's an old file which isn't
            # integration or script
            corresponding_pack_file_object: dict = existing_pack_structure[content_item_entity][content_item_name][0]
            corresponding_pack_file_path: str = corresponding_pack_file_object["path"]

            self.update_data(
                file_path,
                corresponding_pack_file_path,
                is_yaml=(content_item_extension == ".yml"))

            output_path = corresponding_pack_file_path

        else:  # If the content item doesn't exist in the output pack, create a new directory for it
            output_path = Path(self.output_pack_path, content_item_entity)
            output_path.mkdir(parents=True, exist_ok=True)  # Create path if it doesn't exist

        shutil.move(src=file_path, dst=output_path)

        try:  # Clean up temp dir
            shutil.rmtree(temp_dir, ignore_errors=True)

        except shutil.Error as e:
            logger.warning(f"Failed to remove temp dir '{temp_dir}': {e}")
            logger.debug(traceback.format_exc())

            if self.run_format and output_path.suffix in (".yml", ".yaml", ".json"):
                format_manager(
                    input=str(output_path),
                    no_validate=False,
                    assume_answer=False,
                )

        logger.debug(f"Content item '{content_item_name}' was successfully downloaded.")
        return True

    @staticmethod
    def update_data(file_to_update: Path | str, original_file: str, is_yaml: bool) -> None:
        """
        Collects special chosen fields from the file_path_to_read and writes them into the file_path_to_write.

        Args:
            file_to_update (Path | str): Path to the new file to merge 'original_file' into.
            original_file (str): Path to the original file to merge into 'file_to_update'.
            is_yaml (bool): True if the file is a yml file, False if it's a json file.
        """
        file_to_update = Path(file_to_update) if isinstance(file_to_update, str) else file_to_update

        pack_obj_data, _ = get_dict_from_file(original_file)
        fields = (
            DELETED_YML_FIELDS_BY_DEMISTO
            if is_yaml
            else DELETED_JSON_FIELDS_BY_DEMISTO
        )
        # Creates a nested-complex dict of all fields to be deleted by the server.
        # We need the dict to be nested, to easily merge it later to the file data.
        preserved_data: dict = unflatten(
            {
                field: dictor(pack_obj_data, field)
                for field in fields
                if dictor(pack_obj_data, field)
            },
            splitter="dot",
        )

        file_data = get_file(file_to_update)

        if pack_obj_data:
            mergedeep.merge(file_data, preserved_data)

        if is_yaml:
            write_dict(file_to_update, data=file_data, handler=yaml)
        else:  # json
            write_dict(file_to_update, data=file_data, handler=json, indent=4)


    def get_expected_filename(self, content_item_name: str, file_extension: str) -> str:
        """
        Creates a file name to search for in the existing pack.

        Args:
            content_item_name: Content item's name
            file_extension: File's extension

        Returns:
            str: The expected file name
        """
        if file_extension in (".py", ".yml", ".yaml"):
            return f"{self.create_directory_name(content_item_name)}.{file_extension.lstrip('.')}"

        else:  # Description & image files have their type within the file name
            if file_extension == ".md":
                file_type = "description"
            elif file_extension == ".png":
                file_type = "image"
            else:
                file_type = ""
                logger.warning(
                    f"Unsupported file extension '{file_extension}'."
                )

            return f"{self.create_directory_name(content_item_name)}_{file_type}.{file_extension}"

    def remove_traces(self):
        """
        Removes (recursively) all temporary files & directories used across the module
        """
        try:
            shutil.rmtree(self.system_content_temp_dir, ignore_errors=True)
        except shutil.Error as e:
            logger.error(str(e))
            raise
