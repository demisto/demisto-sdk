import ast
import contextlib
import glob
import itertools
import logging
import os
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

import demisto_client
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version
from tabulate import tabulate

from demisto_sdk.commands.common.constants import (
    CLASSIFIERS_DIR,
    CONTENT_ENTITIES_DIRS,
    DASHBOARDS_DIR,
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
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.tools import (
    find_type,
    get_demisto_version,
    get_file,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
)
from demisto_sdk.commands.content_graph.objects.content_item import (
    ContentItem,
    FailedUploadException,
    IncompatibleUploadVersionException,
    NotUploadableException,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack, upload_zipped_pack

logger = logging.getLogger("demisto-sdk")
json = JSON_Handler()


# These are the class names of the objects in demisto_sdk.commands.common.content.objects
UPLOAD_SUPPORTED_ENTITIES = [
    # NOTE: THIS IS NO LONGER IN USE OR MAINAINED. SEE GRAPH OBJECTS INSTEAD
    FileType.INTEGRATION,
    FileType.BETA_INTEGRATION,
    FileType.SCRIPT,
    FileType.TEST_SCRIPT,
    FileType.PLAYBOOK,
    FileType.TEST_PLAYBOOK,
    FileType.OLD_CLASSIFIER,  # TODO check
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
        client (DefaultApi): Demisto-SDK client object.
    """

    def __init__(
        self,
        input: Optional[Path],
        insecure: bool = False,
        pack_names: Optional[List[str]] = None,
        skip_validation: bool = False,
        detached_files: bool = False,
        reattach: bool = False,
        override_existing: bool = False,
        marketplace: MarketplaceVersions = MarketplaceVersions.XSOAR,
        **kwargs,
    ):
        self.path = None if input is None else Path(input)
        verify = (
            (not insecure) if insecure else None
        )  # set to None so demisto_client will use env var DEMISTO_VERIFY_SSL
        self.client = demisto_client.configure(verify_ssl=verify)

        self._successfully_uploaded_content_items: List[Union[ContentItem, Pack]] = []
        self._successfully_uploaded_zipped_packs: List[str] = []

        self._failed_upload_content_items: List[
            Tuple[Union[ContentItem, Pack], str]
        ] = []
        self._failed_upload_version_mismatch: List[ContentItem] = []
        self._failed_upload_zipped_packs: List[str] = []
        self.failed_parsing: List[Tuple[Path, str]] = []

        self.demisto_version = get_demisto_version(self.client)
        self.pack_names: List[str] = pack_names or []
        self.skip_upload_packs_validation = skip_validation
        self.should_detach_files = detached_files
        self.should_reattach_files = reattach
        self.override_existing = override_existing
        self.marketplace = marketplace

    def _upload_zipped(self, path: Path) -> bool:
        """
        Upload a zipped pack to the remote Cortex XSOAR instance.
        Args:
            path (Path): The path of the zipped pack to upload.
        Returns:
            bool: True if the upload was successful, False otherwise.
        """

        def _parse_internal_pack_names(zip_path: Path) -> Tuple[str, ...]:
            with zipfile.ZipFile(zip_path) as zip_file:
                file_names = zip_file.namelist()

                if "pack_metadata.json" in file_names:  # single pack
                    with zip_file.open("pack_metadata.json") as pack_metadata:
                        return json.load(pack_metadata).get("name") or ()

            # multiple packs, zipped
            return tuple(item[:-4] for item in file_names if item.endswith(".zip"))

        pack_names = _parse_internal_pack_names(path)

        try:
            if upload_zipped_pack(
                path=path,
                client=self.client,
                target_demisto_version=Version(str(self.demisto_version)),
                marketplace=self.marketplace,
                skip_validations=True,  # TODO
            ):
                self._successfully_uploaded_zipped_packs.extend(pack_names)
                return True

        except Exception:
            logger.exception(f"Failed uploading {pack_names}")
            self._failed_upload_zipped_packs.extend(pack_names)

        return False

    def upload(self):
        """Upload the pack / directory / file to the remote Cortex XSOAR instance."""
        if self.demisto_version == "0":
            logger.info(
                "[red]Could not connect to XSOAR server. Try checking your connection configurations.[/red]"
            )
            return ERROR_RETURN_CODE

        if not self.path or not self.path.exists():
            logger.error(f"[red]input path: {self.path} does not exist[/red]")
            return ERROR_RETURN_CODE

        if self.should_detach_files:
            item_detacher = ItemDetacher(
                client=self.client, marketplace=self.marketplace
            )
            detached_items_ids = item_detacher.detach(upload_file=True)

            if self.should_reattach_files:
                ItemReattacher(client=self.client).reattach(
                    detached_files_ids=detached_items_ids
                )

            if not self.path:  # Nothing to upload
                return SUCCESS_RETURN_CODE

        logger.info(
            f"Uploading {self.path} to {self.client.api_client.configuration.host}..."
        )

        try:
            if self.path.suffix == ".zip":
                success = self._upload_zipped(self.path)
            elif self.path.is_dir() and is_uploadable_dir(self.path):
                success = self._upload_entity_dir(self.path)
            else:
                success = self._upload_single(self.path)
        except KeyboardInterrupt:
            return ABORTED_RETURN_CODE

        if self.failed_parsing and not any(
            (
                self._successfully_uploaded_content_items,
                self._successfully_uploaded_zipped_packs,
                self._failed_upload_content_items,
                self._failed_upload_version_mismatch,
                self._failed_upload_zipped_packs,
            )
        ):
            # Nothing was uploaded, nor collected as error
            logger.error(
                "\n".join(
                    (
                        "[red]Nothing to upload: the input path should point to one of the following:",
                        "\t1. A Pack",
                        "\t2. A content entity directory that is inside a pack, e.g. Integrations",
                        "\t3. A valid content item file, that can be imported to Cortex XSOAR manually.[/red]",
                    )
                )
            )
            return ERROR_RETURN_CODE

        self.print_summary()
        return SUCCESS_RETURN_CODE if success else ERROR_RETURN_CODE

    def _upload_single(self, path: Path, zipped: bool = False) -> bool:
        """
        Upload a content item, a pack, or a zip containing packs.

        Returns:
            bool: whether the item is uploaded succesfully.

        Raises:
            NotIndivitudallyUploadedException (see exception class)
            NotUploadableException
        """
        content_item: Union[ContentItem, Pack] = BaseContent.from_path(
            path
        )  # type:ignore[assignment]
        if content_item is None:
            reason = (
                "Deprecated type - use LayoutContainer instead"
                if find_type(str(path)) == FileType.LAYOUT
                else "unknown"
            )
            self.failed_parsing.append((path, reason))
            return False

        try:
            content_item.upload(
                client=self.client,
                marketplace=self.marketplace,
                target_demisto_version=Version(str(self.demisto_version)),
                zipped=zipped,  # only used for Packs
            )

            # upon reaching this line, the upload is surely successful
            uploaded_succesfully = (
                iter(content_item.content_items)
                if (isinstance(content_item, Pack) and not zipped)  # TODO not zipped?
                # packs uploaded unzipped are uploaded item by item, we have to extract the item details here
                else (content_item,)
            )

            self._successfully_uploaded_content_items.extend(uploaded_succesfully)
            for item_uploaded_successfully in uploaded_succesfully:
                logger.debug(
                    f"Uploaded {item_uploaded_successfully.content_type} {item_uploaded_successfully.normalize_name} successfully"
                )
            return True

        except KeyboardInterrupt:
            raise  # the functinos calling this one have a special return code for manual interruption

        except IncompatibleUploadVersionException as e:
            logger.error(e)
            assert isinstance(
                content_item, ContentItem
            ), "Cannot compare version for Pack items, only ContentItems"
            self._failed_upload_version_mismatch.append(content_item)
            return False

        except ApiException as e:
            message = f"unknown: {e}"
            with contextlib.suppress(Exception):
                message = parse_error_response(e)
            self._failed_upload_content_items.append((content_item, message))
            return False

        except (FailedUploadException, NotUploadableException, Exception) as e:
            logger.error(str(e))
            self._failed_upload_content_items.append((content_item, str(e)))
            return False

    def _upload_entity_dir(self, path: Path) -> bool:
        """
        Uploads an entity path directory
        Args:
            path: an entity path in the following formats:
                `.../Packs/{Pack_Name}/{Entity_Type}/[optional: entity name]`

        Returns:
            Whether the upload succeeded.

        """
        if not set(path.parts[-2:]).intersection(CONTENT_ENTITIES_DIRS):
            # neither the last, nor second-last are a content entity dir
            raise ValueError(f"Invalid entity dir path: {path}")

        to_upload: Iterable[Path]
        if path.name in {SCRIPTS_DIR, INTEGRATIONS_DIR}:
            # These folders have another level of content
            to_upload = filter(lambda p: p.is_dir(), path.iterdir())
        else:
            to_upload = itertools.chain(path.glob("*.yml"), path.glob("*.json"))

        return all(self._upload_single(item) for item in to_upload)

    def notify_user_should_override_packs(self):  # TODO is used?
        """Notify the user about possible overridden packs."""

        response = self.client.generic_request(
            "/contentpacks/metadata/installed", "GET"
        )
        if installed_packs := eval(response[0]):  # TODO json loads
            installed_packs = {pack["name"] for pack in installed_packs}
            if common_packs := installed_packs.intersection(self.pack_names):
                pack_names = "\n".join(common_packs)
                product = (
                    self.marketplace.lower()
                    .replace(MarketplaceVersions.MarketplaceV2, "XSIAM")
                    .upper()
                )
                logger.debug(
                    f"[red]This command will overwrite the following packs:\n{pack_names}.\n"
                    f"Any changes made on {product} will be lost.[red]"
                )
                if not self.override_existing:
                    logger.info("[red]Are you sure you want to continue? y/[N][/red]")
                    answer = str(input())
                    return answer in {"y", "Y", "yes"}

        return True

    def print_summary(self) -> None:
        """Prints uploaded files summary
        Successful uploads grid based on `successfully_uploaded_files` attribute in green color
        Failed uploads grid based on `failed_uploaded_files` attribute in red color
        """
        logger.info("UPLOAD SUMMARY:\n")

        if (
            self._successfully_uploaded_content_items
            or self._successfully_uploaded_zipped_packs
        ):
            uploaded_str = tabulate(
                (
                    itertools.chain(
                        (
                            (item.path.name, item.content_type)
                            for item in self._successfully_uploaded_content_items
                        ),
                        (
                            (item, "Pack")
                            for item in self._successfully_uploaded_zipped_packs
                        ),
                    )
                ),
                headers=["NAME", "TYPE"],
                tablefmt="fancy_grid",
            )

            logger.info(f"[green]SUCCESSFUL UPLOADS:\n{uploaded_str}\n[/green]")

        if self._failed_upload_version_mismatch:
            version_mismatch_str = tabulate(
                (
                    (
                        item.path.name,
                        item.content_type,
                        self.demisto_version,
                        item.fromversion,
                        item.toversion,
                    )
                    for item in self._failed_upload_version_mismatch
                ),
                headers=[
                    "NAME",
                    "TYPE",
                    "XSOAR Version",
                    "FILE_FROM_VERSION",
                    "FILE_TO_VERSION",
                ],
                tablefmt="fancy_grid",
            )
            logger.info(
                f"[yellow]NOT UPLOADED DUE TO VERSION MISMATCH:\n{version_mismatch_str}\n[/yellow]"
            )

        if self.failed_parsing:
            failed_parsing_str = tabulate(
                ((path.name, path, reason) for path, reason in self.failed_parsing),
                headers=("FILE_NAME", "PATH", "REASON"),
                tablefmt="fancy_grid",
            )
            logger.info(f"[red]FAILED PARSING CONTENT:\n{failed_parsing_str}[/red]")

        if self._failed_upload_content_items or self._failed_upload_zipped_packs:
            failed_upload_str = tabulate(
                (
                    itertools.chain(
                        (
                            (item.path.name, item.content_type, error)
                            for item, error in self._failed_upload_content_items
                        ),
                        (
                            (
                                (item, "Pack", "see logs above")
                                for item in self._failed_upload_zipped_packs
                            )
                        ),
                    )
                ),
                headers=["NAME", "TYPE", "ERROR"],
                tablefmt="fancy_grid",
            )
            logger.info(f"[red]FAILED UPLOADS:\n{failed_upload_str}\n[/red]")


def parse_error_response(error: ApiException) -> str:
    """
    Parses error message from exception raised in call to client to upload a file

    error (ApiException): The exception which was raised in call in to client
    """
    if isinstance(error, KeyboardInterrupt):
        return "Aborted due to keyboard interrupt."

    if hasattr(error, "reason"):
        reason = str(error.reason)
        if "[SSL: CERTIFICATE_VERIFY_FAILED]" in reason:
            return (
                "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate.\n"
                "Run the command with the --insecure flag."
            )

        elif "Failed to establish a new connection:" in reason:
            return (
                "Failed to establish a new connection: Connection refused.\n"
                "Check the BASE url configuration."
            )

        elif reason in ("Bad Request", "Forbidden"):
            error_body = json.loads(error.body)
            message = error_body.get("error", "")

            if error_body.get("status") == 403:
                message += "\nTry checking your API key configuration."
            return message
        return reason
    return str(error)


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
    def __init__(
        self, client, marketplace: MarketplaceVersions, file_path: str = "SystemPacks"
    ):
        self.file_path = file_path
        self.client = client
        self.marketplace = marketplace

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
            logger.info(f"\n[green]File: {file_id} was detached[/green]")
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
        return file_data.get("id")  # TODO get_id

    def detach(self, upload_file: bool = False) -> List[str]:
        detach_files_list: list = []
        if os.path.isdir(self.file_path):
            detach_files_list = self.extract_items_from_dir()
            for file in detach_files_list:
                self.detach_item(file.get("file_id"), file_path=file.get("file_path"))
                if upload_file:
                    Uploader(
                        input=Path(raw_file_path)
                        if (raw_file_path := file.get("file_path")) is not None
                        else None,
                        marketplace=self.marketplace,
                    ).upload()

        elif os.path.isfile(self.file_path):
            file_id = self.find_item_id_to_detach()
            detach_files_list.append({"file_id": file_id, "file_path": self.file_path})
            self.detach_item(file_id=file_id, file_path=self.file_path)
            if upload_file:
                Uploader(
                    input=Path(self.file_path) if self.file_path is not None else None,
                    marketplace=self.marketplace,
                ).upload()

        return [file["file_id"] for file in detach_files_list]


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
            logger.debug(f"\n[green]{item_type}: {item_id} was reattached[/green]")
        except Exception as e:
            raise Exception(f"Exception raised when fetching custom content:\n{e}")

    def reattach(self, detached_files_ids=None):
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


def is_uploadable_dir(path: Path):
    return path.is_dir() and (
        path.name in CONTENT_ENTITIES_DIRS
        or (
            path.name in UNIFIED_ENTITIES_DIR
            and path.parent.name in CONTENT_ENTITIES_DIRS
        )
    )
