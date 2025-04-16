from __future__ import annotations

import re
import shutil
import tarfile
import traceback
from collections import defaultdict
from enum import Enum
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import DefaultDict, Dict

import demisto_client.demisto_api
import mergedeep
import typer
from demisto_client.demisto_api.rest import ApiException
from dictor import dictor
from flatten_dict import unflatten
from tabulate import tabulate
from urllib3 import HTTPResponse
from urllib3.exceptions import MaxRetryError

from demisto_sdk.commands.common.constants import (
    CONTENT_FILE_ENDINGS,
    ENTITY_NAME_SEPARATORS,
    ENTITY_TYPE_TO_DIR,
    INTEGRATIONS_DIR,
    LISTS_DIR,
    PLAYBOOKS_DIR,
    SCRIPTS_DIR,
    TEST_PLAYBOOKS_DIR,
    UUID_REGEX,
    FileType,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.handlers import DEFAULT_YAML_HANDLER as yaml
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_code_lang,
    get_dict_from_file,
    get_display_name,
    get_file,
    get_file_details,
    get_files_in_dir,
    get_id,
    get_json,
    get_yaml,
    get_yml_paths_in_dir,
    is_sdk_defined_working_offline,
    pascal_case,
    safe_read_unicode,
    write_dict,
)
from demisto_sdk.commands.format.format_module import format_manager
from demisto_sdk.commands.init.initiator import Initiator
from demisto_sdk.commands.split.jsonsplitter import JsonSplitter
from demisto_sdk.commands.split.ymlsplitter import YmlSplitter


class ContentItemType(Enum):
    AUTOMATION = "Automation"
    CLASSIFIER = "Classifier"
    FIELD = "Field"
    INCIDENT_TYPE = "IncidentType"
    INDICATOR_TYPE = "IndicatorType"
    LAYOUT = "Layout"
    MAPPER = "Mapper"
    PLAYBOOK = "Playbook"


ITEM_TYPE_TO_ENDPOINT: dict = {
    ContentItemType.AUTOMATION: "automation/load/",
    ContentItemType.CLASSIFIER: "/classifier/search",
    ContentItemType.FIELD: "/incidentfields",
    ContentItemType.INCIDENT_TYPE: "/incidenttype",
    ContentItemType.INDICATOR_TYPE: "/reputation",
    ContentItemType.LAYOUT: "/layouts",
    ContentItemType.MAPPER: "/classifier/search",
    ContentItemType.PLAYBOOK: "/playbook/search",
}

ITEM_TYPE_TO_REQUEST_TYPE = {
    ContentItemType.AUTOMATION: "POST",
    ContentItemType.CLASSIFIER: "POST",
    ContentItemType.FIELD: "GET",
    ContentItemType.INCIDENT_TYPE: "GET",
    ContentItemType.INDICATOR_TYPE: "GET",
    ContentItemType.LAYOUT: "GET",
    ContentItemType.MAPPER: "POST",
    ContentItemType.PLAYBOOK: "GET",
}

# Fields to keep on existing content items when overwriting them with a download (fields that are omitted by the server)
KEEP_EXISTING_JSON_FIELDS = ["fromVersion", "toVersion"]
KEEP_EXISTING_YAML_FIELDS = [
    "fromversion",
    "toversion",
    "alt_dockerimages",
    "tests",
    "defaultclassifier",
    "defaultmapperin",
    "defaultmapperout",
]


def format_playbook_task(content_item_data: dict[str, dict]):
    """This function checks if there are tasks that run sub-playbooks and converts 'playbookId' to 'playbookName' where applicable.
       XSUP-39266: replacing playbookId with playbookName in tasks.

    Args:
        content_item_data (Dict): The content item data containing tasks.
    """
    content_data = content_item_data.get("data", {})
    all_tasks_data = content_data.get("tasks", {})
    if isinstance(all_tasks_data, dict) and all_tasks_data:
        for task_id, task_data in all_tasks_data.items():
            playbook_id_value = task_data.get("task", {}).get("playbookId")
            if task_data.get("type") == "playbook" and playbook_id_value:
                task_data["task"]["playbookName"] = task_data["task"].pop("playbookId")


class Downloader:
    """
    A class for downloading content from an XSOAR / XSIAM server.

    Attributes:
        output_pack_path (str): A path to a pack to save the downloaded content to.
        input_files (list): A list of content item's names (not file names) to download.
        regex (str): A RegEx pattern to use for filtering the custom content files to download.
        force (bool): Whether to overwrite files that already exist in the output pack.
        client (Demisto client): Demisto client objecgt to use for API calls.
        should_list_files (bool): Whether to list all downloadable files or not (if True, all other flags are ignored).
        download_all_custom_content (bool): Whether to download all available custom content.
        should_run_format (bool): Whether to run 'format' on downloaded files.
        download_system_items (bool): Whether the current download is for system items.
        system_item_type (ContentItemType): The items type to download (relevant only for system items).
        should_init_new_pack (bool): Whether to initialize a new pack structure in the output path.
        keep_empty_folders (bool): Whether to keep empty folders when using the 'init' flag.
        auto_replace_uuids (bool):  Whether to replace the UUIDs.
    """

    def __init__(
        self,
        output: str | None = None,
        input: tuple = tuple(),
        regex: str | None = None,
        force: bool = False,
        insecure: bool = False,
        list_files: bool = False,
        all_custom_content: bool = False,
        run_format: bool = False,
        system: bool = False,
        item_type: str | None = None,
        init: bool = False,
        keep_empty_folders: bool = False,
        auto_replace_uuids: bool = True,
        **kwargs,
    ):
        self.output_pack_path = output
        self.input_files = list(input) if input else []
        self.regex = regex
        self.force = force
        self.download_system_items = system
        self.system_item_type = ContentItemType(item_type) if item_type else None
        self.should_list_files = list_files
        self.download_all_custom_content = all_custom_content
        self.should_run_format = run_format
        self.client = demisto_client.configure(verify_ssl=not insecure)
        self.should_init_new_pack = init
        self.keep_empty_folders = keep_empty_folders
        self.auto_replace_uuids = auto_replace_uuids
        if is_sdk_defined_working_offline() and self.should_run_format:
            self.should_run_format = False
            logger.warning(
                "Formatting is not supported when 'DEMISTO_SDK_OFFLINE_ENV' environment variable is set.\n"
                "Downloaded files will not be formatted."
            )

    def download(self) -> int:
        """
        Downloads content items (system or custom) from XSOAR / XSIAM to the provided output path.

        Returns:
            int: Exit code. 1 if failed, 0 if succeeded
        """
        input_files_missing = False  # Used for returning an exit code of 1 if one of the inputs is missing.
        try:
            if self.should_list_files:
                # No flag validations are needed, since only the '-lf' flag is used.
                self.list_all_custom_content()
                raise typer.Exit(0)
            if not self.output_pack_path:
                logger.error("Error: Missing required parameter '-o' / '--output'.")
                raise typer.Exit(1)

            output_path = Path(self.output_pack_path)

            if not self.verify_output_path(output_path=output_path):
                raise typer.Exit(1)

            if self.should_init_new_pack:
                output_path = self.initialize_output_path(root_folder=output_path)

            if self.download_system_items:
                if not self.input_files:
                    logger.error(
                        "Error: Missing required parameter for downloading system items: '-i' / '--input'."
                    )
                    raise typer.Exit(1)

                if not self.system_item_type:
                    logger.error(
                        "Error: Missing required parameter for downloading system items: '-it' / '--item-type'."
                    )
                    raise typer.Exit(1)

                content_item_type = self.system_item_type
                downloaded_content_objects = self.fetch_system_content(
                    content_item_type=content_item_type,
                    content_item_names=self.input_files,
                )

            else:  # Custom content
                if not any(
                    (self.input_files, self.download_all_custom_content, self.regex)
                ):
                    logger.error(
                        "Error: No input parameter has been provided "
                        "('-i' / '--input', '-r' / '--regex', '-a' / '--all)."
                    )
                    raise typer.Exit(1)

                elif self.regex:
                    # Assure regex is valid
                    try:
                        re.compile(self.regex)

                    except re.error:
                        logger.error(
                            f"Error: Invalid regex pattern provided: '{self.regex}'."
                        )
                        raise typer.Exit(1)

                all_custom_content_data = self.download_custom_content()
                all_custom_content_objects = self.parse_custom_content_data(
                    file_name_to_content_item_data=all_custom_content_data
                )

                # Filter custom content so that we'll process only downloaded content
                downloaded_content_objects = self.filter_custom_content(
                    custom_content_objects=all_custom_content_objects
                )
                for _, value in downloaded_content_objects.items():
                    if value["type"] == FileType.PLAYBOOK:
                        format_playbook_task(value)
                if self.input_files:
                    downloaded_content_item_names = [
                        item["name"] for item in downloaded_content_objects.values()
                    ]

                    for content_item in self.input_files:
                        if content_item not in downloaded_content_item_names:
                            logger.warning(
                                f"Custom content item '{content_item}' provided as an input "
                                f"could not be found / parsed."
                            )
                            input_files_missing = True

                if not downloaded_content_objects:
                    logger.info(
                        "No custom content matching the provided input filters was found."
                    )
                    raise typer.Exit(1) if input_files_missing else typer.Exit(0)

                if self.auto_replace_uuids:
                    # Replace UUID IDs with names in filtered content (only content we download)
                    uuid_mapping = self.create_uuid_to_name_mapping(
                        custom_content_objects=all_custom_content_objects
                    )

                    self.replace_uuid_ids(
                        custom_content_objects=downloaded_content_objects,
                        uuid_mapping=uuid_mapping,
                    )

            existing_pack_data = self.build_existing_pack_structure(
                existing_pack_path=output_path
            )

            result = self.write_files_into_output_path(
                downloaded_content_objects=downloaded_content_objects,
                output_path=output_path,
                existing_pack_structure=existing_pack_data,
            )

            if not result:
                logger.error("Download failed.")
                raise typer.Exit(1)

            raise typer.Exit(1) if input_files_missing else typer.Exit(0)

        except typer.Exit:
            # Re-raise typer.Exit without handling it as an error
            raise

        except Exception as e:
            if not isinstance(e, HandledError):
                logger.error(f"Error: {e}")

            logger.debug("Traceback:\n" + traceback.format_exc())
            raise typer.Exit(1)

    def list_all_custom_content(self):
        """
        List all custom content available to download from the configured XSOAR instance.
        """
        all_custom_content_data = self.download_custom_content()
        all_custom_content_objects = self.parse_custom_content_data(
            file_name_to_content_item_data=all_custom_content_data
        )

        logger.info(
            f"List of custom content files available to download ({len(all_custom_content_objects)}):\n"
        )
        custom_content_table = self.create_custom_content_table(
            custom_content_objects=all_custom_content_objects
        )

        logger.info(custom_content_table)

    def filter_custom_content(
        self, custom_content_objects: dict[str, dict]
    ) -> dict[str, dict]:
        """
        Filter custom content data to include only relevant files for the current download command.

        Args:
            custom_content_objects (dict[str, dict]): A dictionary mapping custom content file names
                to their corresponding objects, that will be filtered.

        Returns:
            dict[str, dict]: A new custom content objects dict with filtered items.
        """
        file_name_to_content_name_map = {
            file_name: content_object["name"]
            for file_name, content_object in custom_content_objects.items()
        }
        filtered_custom_content_objects: dict[str, dict] = {}
        original_count = len(custom_content_objects)
        logger.debug(f"Filtering {original_count} custom content items...")

        compiled_regex = re.compile(self.regex) if self.regex else None

        for file_name, content_item_data in custom_content_objects.items():
            content_item_name = file_name_to_content_name_map[file_name]

            # Filter according input / regex flags
            if (
                self.download_all_custom_content
                or (compiled_regex and re.match(compiled_regex, content_item_name))
                or content_item_name in self.input_files
            ):
                filtered_custom_content_objects[file_name] = content_item_data

        logger.info(
            f"Filtering process completed, {len(filtered_custom_content_objects)}/{original_count} items remain."
        )
        return filtered_custom_content_objects

    def create_uuid_to_name_mapping(
        self, custom_content_objects: dict[str, dict]
    ) -> dict[str, str]:
        """
        Find and map UUID IDs of custom content to their names.

        Args:
            custom_content_objects (dict[str, dict]):
                A dictionary mapping custom content names to their corresponding objects.

        Returns:
            dict[str, str]: A dictionary mapping UUID IDs to corresponding names of custom content.
        """
        logger.debug("Creating ID mapping for custom content...")
        mapping: dict[str, str] = {}
        duplicate_ids: list[str] = []

        for content_object in custom_content_objects.values():
            content_item_id = content_object["id"]

            if (
                re.match(UUID_REGEX, content_item_id)
                and content_item_id not in duplicate_ids
            ):
                if content_item_id not in mapping:
                    mapping[content_item_id] = content_object["name"]

                else:
                    logger.warning(
                        f"Found duplicate ID '{content_item_id}' for custom content item '{content_object['name']}'"
                        f" (also references to '{mapping[content_item_id]}').\n"
                        "ID replacements for these content items will be skipped."
                    )
                    duplicate_ids.append(mapping.pop(content_item_id))

        logger.debug("Custom content IDs mapping created successfully.")
        return mapping

    def download_custom_content(self) -> dict[str, StringIO]:
        """
        Download custom content bundle using server's API,
        and create a StringIO object containing file data for each file within it.

        Returns:
            dict[str, StringIO]: A dictionary mapping custom content's file names to their content.
        """
        try:
            logger.info(
                f"Fetching custom content bundle from server ({self.client.api_client.configuration.host})..."
            )

            api_response: HTTPResponse = demisto_client.generic_request_func(
                self.client,
                "/content/bundle",
                "GET",
                _preload_content=False,
            )[0]

        except Exception as e:
            if isinstance(e, ApiException) and e.status == 401:
                logger.error(
                    f"Server authentication error: {e}\n"
                    "Please verify that the required environment variables ('DEMISTO_API_KEY', or "
                    "'DEMISTO_USERNAME' and 'DEMISTO_PASSWORD') are properly configured."
                )

            elif isinstance(e, MaxRetryError):
                logger.error(
                    f"Failed connecting to server: {e}.\n"
                    "Please verify that the environment variable 'DEMISTO_BASE_URL' is properly configured, "
                    "and that the server is accessible.\n"
                    "If the server is using a self-signed certificate, try using the '--insecure' flag."
                )

            else:
                logger.error(f"Error while fetching custom content: {e}")

            raise HandledError from e

        logger.debug("Custom content bundle fetched successfully.")
        logger.debug(
            f"Downloaded content bundle size (bytes): {len(api_response.data)}"
        )

        loaded_files: dict[str, StringIO] = {}

        with tarfile.open(fileobj=BytesIO(api_response.data), mode="r") as tar:
            tar_members = tar.getmembers()
            logger.debug(f"Custom content bundle contains {len(tar_members)} items.")

            for file in tar_members:
                file_name = file.name.lstrip("/")

                if extracted_file := tar.extractfile(file):
                    file_data = StringIO(safe_read_unicode(extracted_file.read()))
                    loaded_files[file_name] = file_data

        logger.debug("Custom content items loaded to memory successfully.")
        return loaded_files

    def replace_uuid_ids(
        self, custom_content_objects: dict[str, dict], uuid_mapping: dict[str, str]
    ):
        """
        Find and replace UUID IDs of custom content items with their names (using the provided mapping).

        Note:
            This method modifies the provided 'custom_content_objects' dictionary.

        Args:
            custom_content_objects (dict[str, dict]): A dictionary mapping custom content names
                to their corresponding objects.
            uuid_mapping (dict[str, str]): A dictionary mapping UUID IDs to corresponding names of custom content.
        """
        changed_uuids_count = 0
        failed_content_items = set()

        for original_file_name, file_object in custom_content_objects.items():
            try:
                if self.replace_uuid_ids_for_item(
                    custom_content_object=file_object, uuid_mapping=uuid_mapping
                ):
                    changed_uuids_count += 1

            except Exception as e:
                # If UUID replacement failed, we skip the file
                logger.warning(
                    f"Could not replace UUID IDs in '{file_object['name']}'. "
                    f"Content item will be skipped.\nError: {e}"
                )
                failed_content_items.add(original_file_name)

        for failed_content_item in failed_content_items:
            custom_content_objects.pop(failed_content_item)

        if changed_uuids_count > 0:
            logger.info(
                f"Replaced UUID IDs with names in {changed_uuids_count} custom content items."
            )

    def replace_uuid_ids_for_item(
        self, custom_content_object: dict, uuid_mapping: dict[str, str]
    ) -> bool:
        """
        Find and replace UUID IDs of custom content items with their names.
        The method first creates a mapping of a UUID to a name, and then replaces all UUIDs using this mapping.

        Args:
            custom_content_object (dict): A single custom content object to update UUIDs in.
            uuid_mapping (dict[str, str]): A dictionary mapping UUID IDs to corresponding names of custom content.

        Returns:
            bool: True if the object was updated, False otherwise.
        """
        content_item_file_content = custom_content_object["file"].getvalue()
        uuid_matches = re.findall(UUID_REGEX, content_item_file_content)

        if uuid_matches:
            for uuid in set(uuid_matches).intersection(uuid_mapping):
                logger.debug(
                    f"Replacing UUID '{uuid}' with '{uuid_mapping[uuid]}' in "
                    f"'{custom_content_object['name']}'"
                )

                if custom_content_object["file_extension"] in ("yml", "yaml"):
                    # Wrap the new ID with quotes for cases where the name contains special characters like ':'.
                    # Handle cases where there are quotes already surrounding the ID (avoid duplicate quotes).
                    for replace_str in (f"'{uuid}'", f'"{uuid}"', uuid):
                        content_item_file_content = content_item_file_content.replace(
                            replace_str, f"'{uuid_mapping[uuid]}'"
                        )

                else:
                    content_item_file_content = content_item_file_content.replace(
                        uuid, uuid_mapping[uuid]
                    )

            # Update ID if it's a UUID
            if custom_content_object["id"] in uuid_mapping:
                custom_content_object["id"] = uuid_mapping[custom_content_object["id"]]

            # Update custom content object
            custom_content_object["file"] = StringIO(content_item_file_content)
            loaded_file_data = get_file_details(
                content_item_file_content,
                full_file_path=custom_content_object["file_name"],
            )
            custom_content_object["data"] = loaded_file_data

            return True
        return False

    def build_request_params(
        self,
        content_item_type: ContentItemType,
        content_item_names: list[str],
    ) -> tuple[str, str, dict]:
        """
        Build request parameters for fetching system content of different types from server.

        Args:
            content_item_type (ContentItemType): The type of system content to fetch.
            content_item_names (list[str]): A list of names of system content to fetch.

        Returns:
            tuple[str, str, dict]: A tuple containing the expected_endpoint, request method, and body for the API call.
        """
        endpoint = ITEM_TYPE_TO_ENDPOINT[content_item_type]
        request_type = ITEM_TYPE_TO_REQUEST_TYPE[content_item_type]

        request_body: dict = {}
        if content_item_type in [
            ContentItemType.CLASSIFIER,
            ContentItemType.MAPPER,
            ContentItemType.PLAYBOOK,
        ]:
            filter_by_names = " or ".join(content_item_names)
            request_body = {"query": f"name:{filter_by_names}"}

        return endpoint, request_type, request_body

    def get_system_automations(self, content_items: list[str]) -> dict[str, dict]:
        """
        Fetch system automations from server.

        Args:
            content_items (list[str]): A list of system automation names to fetch.

        Returns:
            dict[str, dict]: A dictionary mapping downloaded automations file names,
                to corresponding dictionaries containing metadata and content.
        """
        downloaded_automations: list[bytes] = []
        logger.info(
            f"Fetching system automations from server ({self.client.api_client.configuration.host})..."
        )

        for automation in content_items:
            try:
                # This is required due to a server issue where the '/' character
                # is considered a path separator for the expected_endpoint.
                if "/" in automation:
                    raise ValueError(
                        f"Automation name '{automation}' is invalid. "
                        f"Automation names cannot contain the '/' character."
                    )

                endpoint = f"automation/load/{automation}"
                api_response = demisto_client.generic_request_func(
                    self.client,
                    endpoint,
                    "POST",
                    _preload_content=False,
                )[0]

                downloaded_automations.append(api_response.data)

            except Exception as e:
                logger.error(f"Failed to fetch system automation '{automation}': {e}")

        logger.debug(
            f"Successfully fetched {len(downloaded_automations)} system automations."
        )

        content_items_objects: dict[str, dict] = {}

        for downloaded_automation in downloaded_automations:
            automation_bytes_data = StringIO(safe_read_unicode(downloaded_automation))
            automation_data = json.load(automation_bytes_data)

            file_name = self.generate_system_content_file_name(
                content_item_type=ContentItemType.AUTOMATION,
                content_item=automation_data,
            )
            content_object = self.create_content_item_object(
                file_name=file_name,
                file_data=automation_bytes_data,
                _loaded_data=automation_data,
            )
            content_items_objects[file_name] = content_object

        return content_items_objects

    def get_system_playbooks(self, content_items: list[str]) -> dict[str, dict]:
        """
        Fetch system playbooks from server.

        Args:
            content_items (list[str]): A list of names of system playbook to fetch.

        Returns:
            dict[str, dict]: A dictionary mapping downloaded playbooks file names,
                to corresponding dictionaries containing metadata and content.
        """
        downloaded_playbooks: list[bytes] = []
        logger.info(
            f"Fetching system playbooks from server ({self.client.api_client.configuration.host})..."
        )

        for playbook in content_items:
            try:
                # This is required due to a server issue where the '/' character
                # is considered a path separator for the expected_endpoint.
                if "/" in playbook:
                    raise ValueError(
                        f"Playbook name '{playbook}' is invalid. "
                        f"Playbook names cannot contain the '/' character."
                    )

                endpoint = f"/playbook/{playbook}/yaml"
                try:
                    api_response = demisto_client.generic_request_func(
                        self.client,
                        endpoint,
                        "GET",
                        _preload_content=False,
                    )[0]

                except ApiException as err:
                    # handling in case the id and name are not the same,
                    # trying to get the id by the name through a different api call
                    logger.debug(
                        f"API call using playbook's name failed:\n{err}\n"
                        f"Attempting to fetch using playbook's ID..."
                    )

                    playbook_id = self.get_playbook_id_by_playbook_name(playbook)

                    if not playbook_id:
                        logger.debug(f"No matching ID found for playbook '{playbook}'.")
                        raise

                    logger.debug(
                        f"Found matching ID for '{playbook}' - {playbook_id}.\n"
                        f"Attempting to fetch playbook's YAML file using the ID."
                    )

                    endpoint = f"/playbook/{playbook_id}/yaml"
                    api_response = demisto_client.generic_request_func(
                        self.client,
                        endpoint,
                        "GET",
                        _preload_content=False,
                    )[0]

                downloaded_playbooks.append(api_response.data)

            except Exception as e:
                logger.error(f"Failed to fetch system playbook '{playbook}': {e}")

        if len(downloaded_playbooks):
            logger.debug(
                f"Successfully fetched {len(downloaded_playbooks)} system playbooks."
            )

        else:
            logger.info("No system playbooks were downloaded.")

        content_objects: dict[str, dict] = {}

        for downloaded_playbook in downloaded_playbooks:
            playbook_bytes_data = StringIO(safe_read_unicode(downloaded_playbook))
            playbook_data = yaml.load(playbook_bytes_data)

            file_name = self.generate_system_content_file_name(
                content_item_type=ContentItemType.PLAYBOOK,
                content_item=playbook_data,
            )
            content_object = self.create_content_item_object(
                file_name=file_name,
                file_data=playbook_bytes_data,
                _loaded_data=playbook_data,
            )
            content_objects[file_name] = content_object

        return content_objects

    def generate_system_content_file_name(
        self, content_item_type: ContentItemType, content_item: dict
    ) -> str:
        """
        Generate a file name for a download system content item.

        Args:
            content_item_type (ContentItemType): The type of system content item to generate a file name for.
            content_item (dict): The system content item to generate a file name for.

        Returns:
            str: The generated file name.
        """
        item_name: str = content_item.get("name") or content_item["id"]
        suffix = (
            ".yml"
            if content_item_type
            in (ContentItemType.AUTOMATION, ContentItemType.PLAYBOOK)
            else ".json"
        )

        result = item_name.replace("/", "_").replace(" ", "_") + suffix

        # Remove duplicate underscores
        return re.sub(r"_{2,}", "_", result)

    def fetch_system_content(
        self,
        content_item_type: ContentItemType,
        content_item_names: list[str],
    ) -> dict[str, dict]:
        """
        Fetch system content from the server.

        Args:
            content_item_type (ContentItemType): The type of system content to fetch.
            content_item_names (list[str]): A list of names of system content to fetch.

        Returns:
            dict[str, dict]: A dictionary mapping content item's file names, to dictionaries containing metadata
                and content of the item.
        """
        endpoint, request_method, request_body = self.build_request_params(
            content_item_type=content_item_type,
            content_item_names=content_item_names,
        )

        if content_item_type == ContentItemType.AUTOMATION:
            downloaded_content_objects = self.get_system_automations(
                content_items=content_item_names
            )

        elif content_item_type == ContentItemType.PLAYBOOK:
            downloaded_content_objects = self.get_system_playbooks(
                content_items=content_item_names
            )

        else:
            logger.info(
                f"Fetching system items from server ({self.client.api_client.configuration.host})..."
            )
            api_response = demisto_client.generic_request_func(
                self.client,
                endpoint,
                request_method,
                body=request_body,
                response_type="object",
            )[0]

            if content_item_type in (
                ContentItemType.CLASSIFIER,
                ContentItemType.MAPPER,
            ):
                if classifiers_data := api_response.get("classifiers"):
                    downloaded_items = classifiers_data

                else:
                    logger.debug(
                        "Could not find expected 'classifiers' key in API response.\n"
                        f"API response:\n{json.dumps(api_response)}"
                    )
                    downloaded_items = {}

            else:  # content_item_type (ContentItemType) is one of FIELD, INCIDENT_TYPE, INDICATOR_TYPE, LAYOUT:
                # These are system content items that can't be fetched individually,
                # so we fetch & parse all of them, and then filter according to the input.
                downloaded_items = api_response
                logger.debug(
                    f"Successfully fetched {len(downloaded_items)} {content_item_type.value} content items."
                )

            downloaded_content_objects = {}

            for content_item in downloaded_items:
                file_data = StringIO(json.dumps(content_item))

                file_name = self.generate_system_content_file_name(
                    content_item_type=content_item_type,
                    content_item=content_item,
                )
                content_object = self.create_content_item_object(
                    file_name=file_name,
                    file_data=file_data,
                    _loaded_data=content_item,
                )

                if content_object["name"] in content_item_names:
                    downloaded_content_objects[file_name] = content_object

        downloaded_content_names = [
            f"{item['name']}" for item in downloaded_content_objects.values()
        ]
        logger.debug(
            f"Downloaded system content items: {', '.join(downloaded_content_names)}"
        )
        return downloaded_content_objects

    def parse_custom_content_data(
        self, file_name_to_content_item_data: dict[str, StringIO]
    ) -> dict[str, dict]:
        """
        Converts a mapping of file names to raw file data (StringIO),
        into a mapping of file names to custom content objects (parsed & loaded data)

        Note:
            Custom content items with an empty 'type' key are not supported and will be omitted.

        Args:
            file_name_to_content_item_data (dict[str, StringIO]): A dictionary mapping file names to their content.

        Returns:
            dict[str, dict]: A dictionary mapping content item's file names, to dictionaries containing metadata
                about the content item, and file data.
        """
        logger.info("Parsing downloaded custom content data...")
        custom_content_objects: dict[str, dict] = {}

        for file_name, file_data in file_name_to_content_item_data.items():
            try:
                logger.debug(f"Parsing '{file_name}'...")
                custom_content_object: Dict = self.create_content_item_object(
                    file_name=file_name, file_data=file_data
                )

                # Check if all required fields are present
                missing_field = False
                for _field in ("id", "name", "entity", "type"):
                    if not custom_content_object.get(_field):
                        logger.warning(
                            f"'{file_name}' will be skipped as its {_field} could not be detected."
                        )
                        missing_field = True
                        break

                # If the content is missing a required field, skip it
                if missing_field:
                    continue

                # If the content is written in JavaScript (not supported), skip it
                if custom_content_object["type"] in (
                    FileType.INTEGRATION,
                    FileType.SCRIPT,
                ) and custom_content_object.get("code_lang") in (None, "javascript"):
                    logger.warning(
                        f"Skipping '{file_name}' as JavaScript content is not supported."
                    )
                    continue

                custom_content_objects[file_name] = custom_content_object

            except Exception as e:
                # We fail the whole download process, since we might miss UUIDs to replace if not.
                logger.error(f"Error while parsing '{file_name}': {e}")
                raise

        logger.info(
            f"Successfully parsed {len(custom_content_objects)} custom content objects."
        )
        return custom_content_objects

    def create_custom_content_table(
        self, custom_content_objects: dict[str, dict]
    ) -> str:
        """
        Create a printable list of all custom content that's available to download
        from the configured XSOAR / XSIAM instance.

        Args:
            custom_content_objects (dict[str, dict]): A dictionary mapping custom content's file names to objects.

        Returns:
            str: A printable list of all custom content that's available to download from the configured instance.
        """
        tabulate_data: list[list[str]] = []

        for file_name, file_object in custom_content_objects.items():
            if item_name := file_object.get("name"):
                file_type: FileType = file_object["type"]
                tabulate_data.append([item_name, file_type.value])

        return tabulate(tabulate_data, headers=["Content Name", "Content Type"])

    def initialize_output_path(self, root_folder: Path) -> Path:
        """
        Initialize output path with pack structure.

        Args:
            root_folder (Path): The root folder to initialize the pack structure in.

        Returns:
            Path: Path to the initialized output path.
        """
        logger.debug("Initiating pack structure...")

        if root_folder.name != "Packs":
            root_folder = root_folder / "Packs"

            try:
                root_folder.mkdir(exist_ok=True)

            except FileNotFoundError as e:
                e.filename = str(Path(e.filename).parent)
                raise

        initiator = Initiator(str(root_folder))
        initiator.init()
        generated_path = Path(initiator.full_output_path)

        if not self.keep_empty_folders:
            self.remove_empty_folders(pack_folder=generated_path)

        logger.info(f"Pack structure initialized at '{generated_path}'.")
        return generated_path

    def remove_empty_folders(self, pack_folder: Path) -> None:
        """
        Remove empty folders from the output path.

        Args:
            pack_folder (Path): The pack folder to remove empty folders from.
        """
        for folder_path in pack_folder.glob("*"):
            if folder_path.is_dir() and not any(folder_path.iterdir()):
                folder_path.rmdir()

    def verify_output_path(self, output_path: Path) -> bool:
        """
        Assure that the output path entered by the user is inside a "Packs" folder.

        Args:
            output_path (Path): The output path to check.

        Returns:
            bool: True if the output path is valid, False otherwise.
        """
        if not output_path.is_dir():
            logger.error(
                f"Error: Path '{output_path.absolute()}' does not exist, or isn't a directory."
            )
            return False

        elif not output_path.parent.name == "Packs":
            logger.error(
                f"Error: Path '{output_path.absolute()}' is invalid.\n"
                f"The provided output path for the download must be inside a 'Packs' folder. e.g., 'Packs/MyPack'."
            )
            return False

        return True

    def build_existing_pack_structure(
        self, existing_pack_path: Path
    ) -> dict[str, dict[str, list[dict]]]:
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
        logger.info(f"Parsing existing content in '{existing_pack_path}'...")
        pack_structure: DefaultDict[str, dict[str, list]] = defaultdict(dict)

        for content_entity_path in existing_pack_path.iterdir():
            if content_entity_path.is_dir():
                directory_name = content_entity_path.name

                if directory_name in (INTEGRATIONS_DIR, SCRIPTS_DIR, LISTS_DIR):
                    # If entity is of type integration/script it will have dirs, otherwise files
                    directory_items = [
                        p for p in content_entity_path.iterdir() if p.is_dir()
                    ]
                else:
                    directory_items = [
                        p for p in content_entity_path.iterdir() if p.is_file()
                    ]

                for entity_instance_path in directory_items:
                    content_data = self.build_pack_content_object(
                        content_entity=directory_name,
                        entity_instance_path=entity_instance_path,
                    )

                    if content_data is not None:
                        content_name, content_object = content_data
                        pack_structure[directory_name][content_name] = content_object

        logger.debug("Parsing of existing content items completed.")
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

        metadata = self.get_metadata_file(
            content_type=content_entity, content_item_path=entity_instance_path
        )

        if not metadata:
            logger.warning(
                f"Skipping '{entity_instance_path}' as its metadata file could not be found."
            )
            return None

        content_item_id = get_id(file_content=metadata)
        content_item_name = get_display_name(file_path="", file_data=metadata)

        # if main file doesn't exist/no entity instance path exist the content object won't be added to the pack content
        if not all((content_item_id, content_item_name, file_paths)):
            logger.debug(
                f"Existing content item '{content_item_name}' could not be parsed."
            )
            return None

        content_item_files = []

        for file_path in file_paths:
            file_path_obj = Path(file_path)

            content_item_files.append(
                {
                    "name": content_item_name,
                    "id": content_item_id,
                    "path": file_path_obj,
                    "file_extension": file_path_obj.suffix.lstrip("."),
                }
            )

        return content_item_name, content_item_files

    def get_playbook_id_by_playbook_name(self, playbook_name: str) -> str | None:
        """
        Extract the playbook id by name, calling the api returns an object that cannot be parsed properly,
        and its use is only for extracting the id.

        Args:
            playbook_name (str): The name of a playbook

        Returns:
            str | None: The ID of a playbook
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

        playbook_id = playbooks[0]["id"]
        logger.info(f"Found playbook ID '{playbook_id}' for '{playbook_name}'")
        return playbook_id

    @staticmethod
    def get_metadata_file(content_type: str, content_item_path: Path) -> dict | None:
        """
        Returns the data of the "main" file containing metadata for a content item's path.
        For example, YAML file for integrations / scripts, playbook file for playbooks, etc.

        Args:
            content_type (str): The type of the content item.
            content_item_path (Path): The path to the content item.

        Returns:
            dict | None: The data of the "main" file. None if the file could not be found / parsed.
        """
        if content_type in (
            INTEGRATIONS_DIR,
            SCRIPTS_DIR,
            PLAYBOOKS_DIR,
            TEST_PLAYBOOKS_DIR,
        ):
            if content_item_path.is_dir():
                main_file_path = get_yml_paths_in_dir(content_item_path)[1]

                if not main_file_path:
                    return None

                return get_yaml(main_file_path)

            elif content_item_path.is_file():
                return get_yaml(content_item_path)

        else:
            if content_type == LISTS_DIR and content_item_path.is_dir():
                # Collect json files to return the list metadata
                json_files = [
                    path
                    for path in content_item_path.iterdir()
                    if path.suffix == ".json" and not path.stem.endswith("_data")
                ]
                if not json_files:
                    return None
                return get_json(str(json_files[0]))

            if content_item_path.is_file() and content_item_path.suffix == ".json":
                return get_json(content_item_path)
        return None

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

    def create_content_item_object(
        self, file_name: str, file_data: StringIO, _loaded_data: dict | None = None
    ) -> dict:
        """
        Convert a single custom content item to a content object.

        Args:
            file_name (str): The file name of the custom content item.
            file_data (StringIO): The file data of the custom content item.
            _loaded_data (dict | None, optional): The loaded data of the custom content item.
                If not provided, the file will be parsed.

        Returns:
            dict: The custom content object.
        """
        file_extension = Path(file_name).suffix.lstrip(".")

        if _loaded_data:
            loaded_file_data = _loaded_data

        else:
            loaded_file_data = get_file_details(
                file_content=file_data.getvalue(), full_file_path=file_name
            )

            if not loaded_file_data:
                raise ValueError(f"File '{file_extension}' could not be parsed.")

        file_type = find_type(
            path=file_name, _dict=loaded_file_data, file_type=file_extension
        )
        content_id = get_id(file_content=loaded_file_data)

        # For integrations, 'get_display_name' returns the 'display' field, but we use the 'name' field.
        if file_type == FileType.INTEGRATION:
            content_name = loaded_file_data.get("name")

        else:
            content_name = get_display_name(
                file_path=file_name, file_data=loaded_file_data
            )

        file_entity: str | None

        if (
            file_type == FileType.PLAYBOOK
            and content_name
            and (
                content_name.lower().endswith(("test", "_test", "-test"))
                or content_name.lower().startswith("test")
            )
        ):
            file_entity = TEST_PLAYBOOKS_DIR

        elif file_type:
            file_entity = ENTITY_TYPE_TO_DIR.get(file_type)

        else:
            file_entity = None

        if not content_id:
            logger.warning(f"Could not find the ID of '{file_name}'.")

        custom_content_object: dict = {
            "id": content_id,  # str | None
            "name": content_name,  # str | None
            "entity": file_entity,  # str | None
            "type": file_type,  # FileType | None
            "file": file_data,  # StringIO
            "file_name": self.update_file_prefix(file_name),  # str
            "file_extension": file_extension,  # str
            "data": loaded_file_data,  # dict
        }

        if file_entity and (
            file_code_language := get_code_lang(loaded_file_data, file_entity)
        ):
            custom_content_object["code_lang"] = file_code_language

        return custom_content_object

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

    def write_files_into_output_path(
        self,
        downloaded_content_objects: dict[str, dict],
        existing_pack_structure: dict[str, dict[str, list[dict]]],
        output_path: Path,
    ) -> bool:
        """
        Download the files after processing is done to the output directory.
        For integrations / scripts, YAML extraction is done.
        Content items that already exist in the output pack, will be skipped, unless the '--force' flag is used.
        If it is, the existing and downloaded YAML files will be merged, as some fields are deleted by the server.

        Args:
            downloaded_content_objects (dict[str, dict]): A dictionary of content objects to download.
            existing_pack_structure (dict[str, list]): A dictionary of existing content objects in the output path.
            output_path (Path): The output path to write the files to.

        Returns:
            bool: True if all files were downloaded successfully, False otherwise.
        """
        logger.info("Saving downloaded files to output path...")
        successful_downloads_count = 0
        existing_files_skipped_count = 0
        failed_downloads_count = 0

        with TemporaryDirectory() as temp_dir_str:
            temp_dir = Path(temp_dir_str)

            for file_name, content_object in downloaded_content_objects.items():
                content_item_name: str = content_object["name"]
                content_item_entity: str = content_object["entity"]
                content_item_type: FileType = content_object["type"]

                content_item_exists = (  # Content item already exists in output pack
                    content_item_name
                    in existing_pack_structure.get(content_item_entity, {})
                )

                if content_item_exists and not self.force:
                    logger.debug(
                        f"File '{content_item_name}' will be skipped as it already exists in output pack."
                    )
                    existing_files_skipped_count += 1
                    continue

                downloaded_files: list[Path] = []

                try:
                    if content_item_exists and content_item_type != FileType.LISTS:
                        # We skip 'download_existing_content_items' logic for lists since 'smart-merge' is irrelevant for lists
                        downloaded_files = self.download_existing_content_items(
                            content_object=content_object,
                            existing_pack_structure=existing_pack_structure,
                            output_path=output_path,
                            temp_dir=temp_dir,
                        )

                    else:
                        downloaded_files = self.download_new_content_items(
                            content_object=content_object,
                            output_path=output_path,
                        )
                except Exception as e:
                    failed_downloads_count += 1
                    logger.error(
                        f"Failed to download content item '{content_item_name}': {str(e)}"
                    )
                    logger.debug(traceback.format_exc())
                    continue

                successful_downloads_count += 1

                if self.should_run_format:
                    for downloaded_file in downloaded_files:
                        format_manager(
                            input=str(downloaded_file),
                            no_validate=False,
                            assume_answer=False,
                            clear_cache=True,
                        )

        summary_log = ""

        if successful_downloads_count:
            summary_log = f"Successful downloads: {successful_downloads_count}\n"

        # Files that were skipped due to already existing in the output path.
        if existing_files_skipped_count:
            summary_log += f"Skipped downloads: {existing_files_skipped_count}\n"

        if failed_downloads_count:
            summary_log += f"Failed downloads: {failed_downloads_count}\n"

        # If for there was nothing to attempt to download at all.
        # Can occur if files are skipped due to unexpected errors.
        if not summary_log:
            summary_log = "No files were downloaded."

        logger.info(summary_log.rstrip("\n"))

        return (
            not failed_downloads_count
        )  # Return True if no downloads failed, False otherwise.

    def download_new_content_items(
        self,
        content_object: dict,
        output_path: Path,
    ) -> list[Path]:
        """
        Download new content items to disk. Unified content items will be split into separate files.

        Args:
            content_object (dict): The content object to download
            output_path (Path): The output path to write the files to.

        Returns:
            list[Path]: List of paths to the downloaded content items.
        """
        content_item_name: str = content_object["name"]
        content_item_file_name: str = content_object["file_name"]
        content_item_entity_directory: str = content_object["entity"]
        content_item_type: FileType = content_object["type"]
        content_item_file_data: StringIO = content_object["file"]

        downloaded_files: list[Path] = []

        # If content item is an integration / script, split the unified content item into separate files
        if content_item_entity_directory in (INTEGRATIONS_DIR, SCRIPTS_DIR):
            content_item_directory_name = self.create_directory_name(content_item_name)
            download_path = (
                output_path
                / content_item_entity_directory
                / content_item_directory_name
            )
            download_path.mkdir(parents=True, exist_ok=True)

            extractor = YmlSplitter(
                input=content_item_file_name,
                output=str(download_path),
                input_file_data=content_object["data"],
                file_type=content_item_type.value,
                base_name=content_item_directory_name,
                no_readme=False,
                no_auto_create_dir=True,
            )
            extractor.extract_to_package_format()

            # Add items to downloaded_files
            for file_path in download_path.iterdir():
                if file_path.is_file():
                    downloaded_files.append(file_path)

        elif content_item_entity_directory == LISTS_DIR:
            download_path = (
                output_path
                / content_item_entity_directory
                / pascal_case(content_item_name)
            )
            download_path.mkdir(parents=True, exist_ok=True)

            JsonSplitter(
                input=content_item_file_name,
                output=download_path,
                no_auto_create_dir=True,
                file_type=content_item_type,
                input_file_data=content_object["data"],
            ).split_json()

            for file_path in download_path.iterdir():
                if file_path.is_file():
                    downloaded_files.append(file_path)

        else:
            content_item_download_path = (
                output_path / content_item_entity_directory / content_item_file_name
            )
            content_item_download_path.parent.mkdir(parents=True, exist_ok=True)
            content_item_download_path.write_text(content_item_file_data.getvalue())

            downloaded_files.append(content_item_download_path)

        return downloaded_files

    def download_existing_content_items(
        self,
        content_object: dict,
        existing_pack_structure: dict[str, dict[str, list[dict]]],
        output_path: Path,
        temp_dir: Path,
    ) -> list[Path]:
        """
        Download existing content items to disk.
        Unified content items will be split into separate files.
        Existing content items will be skipped if 'should_overwrite_existing' is False.
        A "smart" merge will be done for pre-existing YAML & JSON files, adding fields that exist in existing file,
        but were omitted by the server.

        Args:
            content_object (dict): The content object to download
            existing_pack_structure (list[dict]): A list of existing content item files in the output pack.
            output_path (Path): The output path to write the files to.
            temp_dir (Path): A temporary directory to use for downloading the content item.

        Returns:
            list[Path]: List of paths to the downloaded content items.
        """
        content_item_name: str = content_object["name"]
        content_item_file_name: str = content_object["file_name"]
        content_item_entity_directory: str = content_object["entity"]
        content_item_type: FileType = content_object["type"]
        content_item_file_data: StringIO = content_object["file"]
        source_to_destination_mapping: dict[
            Path, Path
        ] = {}  # A mapping of temp file paths to target final paths
        is_unified = content_item_entity_directory in (INTEGRATIONS_DIR, SCRIPTS_DIR)

        # If content item is an integration / script, split the unified content item into separate files
        if is_unified:
            content_item_directory_name = self.create_directory_name(content_item_name)
            temp_download_path = (
                temp_dir / content_item_entity_directory / content_item_directory_name
            )
            temp_download_path.mkdir(parents=True, exist_ok=True)

            extractor = YmlSplitter(
                input=content_item_file_name,
                output=str(temp_download_path),
                input_file_data=content_object["data"],
                file_type=content_item_type.value,
                base_name=content_item_directory_name,
                no_readme=True,
                no_auto_create_dir=True,
            )
            extractor.extract_to_package_format()

            for file_path in temp_download_path.iterdir():
                if file_path.is_file():
                    extracted_item_expected_filename = Path(
                        self.get_split_item_expected_filename(
                            content_item_name=content_item_name,
                            file_extension=file_path.suffix,
                        )
                    )

                    source_to_destination_mapping[file_path] = (
                        output_path
                        / content_item_entity_directory
                        / content_item_directory_name
                        / extracted_item_expected_filename
                    )

        else:  # Non-unified content item
            temp_download_path = (
                temp_dir / content_item_entity_directory / content_item_file_name
            )
            temp_download_path.parent.mkdir(parents=True, exist_ok=True)
            temp_download_path.write_text(content_item_file_data.getvalue())

            source_to_destination_mapping[temp_download_path] = (
                output_path / content_item_entity_directory / content_item_file_name
            )

        for source_path, destination_path in source_to_destination_mapping.items():
            source_path_suffix = source_path.suffix.lstrip(".")
            if source_path_suffix in ("json", "yml", "yaml"):
                for existing_file_object in existing_pack_structure[
                    content_item_entity_directory
                ][content_item_name]:
                    existing_file_path: Path = existing_file_object["path"]

                    if existing_file_object["path"].name == destination_path.name:
                        self.preserve_fields(
                            file_to_update=source_path,
                            original_file=existing_file_path,
                            is_yaml=source_path_suffix in ("yml", "yaml"),
                        )
            shutil.move(
                src=str(source_path),
                dst=str(destination_path),
            )

        logger.debug(f"Content item '{content_item_name}' was successfully downloaded.")
        return list(source_to_destination_mapping.values())

    @staticmethod
    def preserve_fields(
        file_to_update: Path, original_file: Path, is_yaml: bool
    ) -> None:
        """
        Preserve specific fields from the 'original_file' and add their values to 'file_to_update'.

        Args:
            file_to_update (Path): Path to the new file to merge 'original_file' into.
            original_file (Path): Path to the original file to merge into 'file_to_update'.
            is_yaml (bool): True if the file is a yml file, False if it's a json file.
        """
        original_file_data = get_dict_from_file(str(original_file))[0]
        fields_to_preserve = (
            KEEP_EXISTING_YAML_FIELDS if is_yaml else KEEP_EXISTING_JSON_FIELDS
        )
        # Creates a nested-complex dict of all fields to be deleted by the server.
        # We need the dict to be nested, to easily merge it later to the file data.
        preserved_data: dict = unflatten(
            {
                field: dictor(original_file_data, field)
                for field in fields_to_preserve
                if dictor(original_file_data, field)
            },
            splitter="dot",
        )

        file_data = get_file(file_to_update)

        if original_file_data:
            mergedeep.merge(file_data, preserved_data)

        if is_yaml:
            write_dict(file_to_update, data=file_data, handler=yaml)
        else:  # json
            write_dict(file_to_update, data=file_data, handler=json, indent=4)

    def get_split_item_expected_filename(
        self, content_item_name: str, file_extension: str
    ) -> str:
        """
        Creates a file name to search for in the existing pack.

        Args:
            content_item_name: Content item's name
            file_extension: File's extension

        Returns:
            str: The expected file name
        """
        if file_extension.lstrip(".") in ("py", "ps1", "js", "yml", "yaml"):
            return f"{self.create_directory_name(content_item_name)}.{file_extension.lstrip('.')}"

        else:  # Description & image files have their type within the file name
            if file_extension == ".md":
                file_type = "description"
            elif file_extension == ".png":
                file_type = "image"
            else:
                file_type = ""
                logger.warning(f"Unsupported file extension '{file_extension}'.")

            return f"{self.create_directory_name(content_item_name)}_{file_type}.{file_extension.lstrip('.')}"


class HandledError(Exception):
    """An exception that has already been handled & logged."""
