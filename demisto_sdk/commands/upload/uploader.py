import ast
import glob
import itertools
import os
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union

import demisto_client
import typer
from demisto_client.demisto_api.rest import ApiException
from packaging.version import Version
from tabulate import tabulate

from demisto_sdk.commands.common.constants import (
    CONTENT_ENTITIES_DIRS,
    INTEGRATIONS_DIR,
    LISTS_DIR,
    SCRIPTS_DIR,
    FileType,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.handlers import DEFAULT_JSON_HANDLER as json
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    find_type,
    get_demisto_version,
    get_file,
    string_to_bool,
)
from demisto_sdk.commands.content_graph.common import (
    ContentType,
)
from demisto_sdk.commands.content_graph.objects.base_content import (
    BaseContent,
)
from demisto_sdk.commands.content_graph.objects.content_item import (
    ContentItem,
)
from demisto_sdk.commands.content_graph.objects.exceptions import (
    FailedUploadException,
    FailedUploadMultipleException,
)
from demisto_sdk.commands.content_graph.objects.pack import Pack, upload_zip
from demisto_sdk.commands.upload.constants import CONTENT_TYPES_EXCLUDED_FROM_UPLOAD
from demisto_sdk.commands.upload.exceptions import (
    IncompatibleUploadVersionException,
    NotUploadableException,
)
from demisto_sdk.commands.upload.tools import parse_error_response

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
        zip: bool = False,
        tpb: bool = False,
        destination_zip_dir: Optional[Path] = None,
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
        self._skipped_upload_marketplace_mismatch: List[ContentItem] = []
        self._failed_upload_zips: List[str] = []
        self.failed_parsing: List[Tuple[Path, str]] = []

        self.demisto_version = get_demisto_version(self.client)
        self.pack_names: List[str] = pack_names or []
        self.skip_upload_packs_validation = skip_validation
        self.should_detach_files = detached_files
        self.should_reattach_files = reattach
        self.override_existing = override_existing
        self.marketplace = marketplace
        self.zip = zip  # -z flag
        self.tpb = tpb  # -tpb flag
        self.destination_zip_dir = destination_zip_dir

    def _upload_zipped(self, path: Path) -> bool:
        """
        Upload a zipped pack to the remote Cortex XSOAR instance.
        Args:
            path (Path): The path of the zipped pack to upload.
        Returns:
            bool: True if the upload was successful, False otherwise.
        """

        def notify_user_should_override_packs():
            """Notify the user about possible overridden packs."""

            if (
                response := self.client.generic_request(
                    "/contentpacks/metadata/installed", "GET", response_type="object"
                )
            ) and response[0]:
                installed_packs = {pack["name"] for pack in response[0]}
                common_packs = installed_packs.intersection({path.stem})
                if common_packs:
                    pack_names = "\n".join(sorted(common_packs))
                    product = (
                        self.marketplace.lower()
                        .replace(MarketplaceVersions.MarketplaceV2, "XSIAM")
                        .upper()
                    )
                    logger.info(
                        "\n".join(
                            (
                                "<red>This command will overwrite the following packs:",
                                pack_names,
                                f"All changes made in these content items on {product} will be lost.</red>",
                            )
                        )
                    )
                    if not self.override_existing:
                        logger.info(
                            "<red>Are you sure you want to continue? y/[N]</red>"
                        )
                        return string_to_bool(str(input()), default_when_empty=False)
            return True

        def _parse_internal_pack_names(zip_path: Path) -> Optional[Tuple[str, ...]]:
            """
            A zip can be
            1. A single pack (just the pack folder zipped); in this case, we parse the name from the pack_metatada.json file
            2. Multiple zipped packs (each in its own .zip file); in this case, we use the names of the inner zips as pack names

            On failure to parse, returns None.
            """
            try:
                with zipfile.ZipFile(zip_path) as zip_file:
                    file_names = zip_file.namelist()

                    if "pack_metadata.json" in file_names:  # single pack
                        with zip_file.open("pack_metadata.json") as pack_metadata:
                            return (json.load(pack_metadata).get("name"),)

                # multiple packs, zipped
                return (
                    tuple(item[:-4] for item in file_names if item.endswith(".zip"))
                    or None
                )

            except Exception:
                logger.debug(f"failed extracting pack names from {zip_path}")
                return None

        pack_names = _parse_internal_pack_names(path) or (path.name,)
        if not notify_user_should_override_packs():
            return False

        try:
            if upload_zip(
                path=path,
                client=self.client,
                target_demisto_version=Version(str(self.demisto_version)),
                skip_validations=True,
                marketplace=self.marketplace,
            ):
                self._successfully_uploaded_zipped_packs.extend(pack_names)
                return True

        except Exception:
            logger.exception(f"Failed uploading {pack_names}")
            self._failed_upload_zips.extend(pack_names)

        return False

    def upload(self):
        """Upload the pack / directory / file to the remote Cortex XSOAR instance."""
        if self.demisto_version.base_version == "0":
            logger.info(
                "<red>Could not connect to the server. Try checking your connection configurations.</red>"
            )
            raise typer.Exit(ERROR_RETURN_CODE)

        if not self.path or not self.path.exists():
            logger.error(f"<red>input path: {self.path} does not exist</red>")
            raise typer.Exit(ERROR_RETURN_CODE)

        if self.should_detach_files:
            item_detacher = ItemDetacher(
                client=self.client, marketplace=self.marketplace
            )
            detached_items_ids = item_detacher.detach(upload_file=True)

            if self.should_reattach_files:
                ItemReattacher(client=self.client).reattach(
                    detached_files_ids=detached_items_ids
                )

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
            raise typer.Exit(ABORTED_RETURN_CODE)

        if self.failed_parsing and not any(
            (
                self._successfully_uploaded_content_items,
                self._successfully_uploaded_zipped_packs,
                self._failed_upload_content_items,
                self._failed_upload_version_mismatch,
                self._failed_upload_zips,
            )
        ):
            # Nothing was uploaded, nor collected as error
            logger.error(
                "\n".join(
                    (
                        "<red>Nothing to upload: the input path should point to one of the following:",
                        "\t1. A Pack",
                        "\t2. A content entity directory that is inside a pack, e.g. Integrations",
                        "\t3. A valid content item file, that can be imported to Cortex XSOAR manually.</red>",
                    )
                )
            )
            raise typer.Exit(ERROR_RETURN_CODE)

        self.print_summary()
        raise (
            typer.Exit(SUCCESS_RETURN_CODE)
            if success
            else typer.Exit(ERROR_RETURN_CODE)
        )

    def _upload_single(self, path: Path) -> bool:
        """
        Upload a content item, a pack, or a zip containing packs.

        Returns:
            bool: whether the item is uploaded succesfully to the relevant
            given marketplace.

        Raises:
            NotIndivitudallyUploadedException (see exception class)
            NotUploadableException
        """
        content_item: Union[ContentItem, Pack] = BaseContent.from_path(path)  # type:ignore[assignment]
        if content_item is None:
            reason = (
                "Deprecated type - use LayoutContainer instead"
                if find_type(str(path)) == FileType.LAYOUT
                else "unknown"
            )
            self.failed_parsing.append((path, reason))
            return False
        if (
            self.marketplace
            and isinstance(content_item, ContentItem)
            and self.marketplace not in content_item.marketplaces
        ):
            self._skipped_upload_marketplace_mismatch.append(content_item)
            return True
        try:
            content_item.upload(
                client=self.client,
                marketplace=self.marketplace,
                target_demisto_version=Version(str(self.demisto_version)),
                zip=self.zip,  # only used for Packs
                tpb=self.tpb,  # only used for Packs
                destination_zip_dir=self.destination_zip_dir,  # only used for Packs
            )

            # upon reaching this line, the upload is surely successful
            uploaded_successfully = parse_uploaded_successfully(
                content_item=content_item, zip=self.zip, tpb=self.tpb
            )
            self._successfully_uploaded_content_items.extend(uploaded_successfully)
            for item_uploaded_successfully in uploaded_successfully:
                logger.debug(
                    f"Uploaded {item_uploaded_successfully.content_type} {item_uploaded_successfully.normalize_name} successfully"
                )
            return True

        except KeyboardInterrupt:
            raise  # the functinos calling this one have a special return code for manual interruption

        except IncompatibleUploadVersionException:
            assert isinstance(
                content_item, ContentItem
            ), "This exception should only be raised for content items"
            self._failed_upload_version_mismatch.append(content_item)
            return False

        except ApiException as e:
            self._failed_upload_content_items.append(
                (content_item, parse_error_response(e))
            )
            return False

        except FailedUploadMultipleException as e:
            for failure in e.upload_failures:
                failure_str = failure.additional_info or str(failure)

                _failed_content_item: Union[Pack, ContentItem, None] = (
                    BaseContent.from_path(failure.path)  # type:ignore[assignment]
                )

                if _failed_content_item is None:
                    self.failed_parsing.append((failure.path, failure_str))
                else:
                    self._failed_upload_content_items.append(
                        (_failed_content_item, failure_str)
                    )
            for failure_mismatch in e.incompatible_versions_items:
                self._failed_upload_version_mismatch.append(failure_mismatch.item)

            self._successfully_uploaded_content_items.extend(e.uploaded_successfully)
            return False

        except (FailedUploadException, NotUploadableException, Exception) as e:
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
        elif path.name == LISTS_DIR:
            to_upload = path.iterdir()
        else:
            to_upload = itertools.chain(path.glob("*.yml"), path.glob("*.json"))

        return all(self._upload_single(item) for item in to_upload)

    def notify_user_should_override_packs(self):
        """Notify the user about possible overridden packs."""

        response = self.client.generic_request(
            "/contentpacks/metadata/installed", "GET"
        )
        if installed_packs := json.loads(response[0]):
            installed_packs = {pack["name"] for pack in installed_packs}
            if common_packs := installed_packs.intersection(self.pack_names):
                pack_names = "\n".join(common_packs)
                product = (
                    self.marketplace.lower()
                    .replace(MarketplaceVersions.MarketplaceV2, "XSIAM")
                    .upper()
                )
                logger.debug(
                    f"<red>This command will overwrite the following packs:\n{pack_names}.\n"
                    f"Any changes made on {product} will be lost.</red>"
                )
                if not self.override_existing:
                    logger.info("<red>Are you sure you want to continue? y/[N]</red>")
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
                            (
                                item.path.name,
                                item.content_type,
                                item.pack_name,
                                item.pack_version,
                            )
                            for item in self._successfully_uploaded_content_items
                        ),
                        (
                            (
                                item,
                                "Pack",
                                item,
                                "",  # When uploading zips we are not aware of the version
                            )
                            for item in self._successfully_uploaded_zipped_packs
                        ),
                    )
                ),
                headers=["NAME", "TYPE", "PACK NAME", "PACK VERSION"],
                tablefmt="fancy_grid",
            )

            logger.info(f"<green>SUCCESSFUL UPLOADS:\n{uploaded_str}\n</green>")

        if self._skipped_upload_marketplace_mismatch:
            marketplace_mismatch_str = tabulate(
                (
                    (
                        item.path.name,
                        item.content_type,
                        self.marketplace,
                        ",".join(
                            [marketplace.value for marketplace in item.marketplaces]
                        ),
                    )
                    for item in self._skipped_upload_marketplace_mismatch
                ),
                headers=[
                    "Name",
                    "Type",
                    "Upload Destination Marketplace",
                    "Content Marketplace(s)",
                ],
                tablefmt="fancy_grid",
            )
            logger.info(
                f"<yellow>SKIPPED UPLOADING DUE TO MARKETPLACE MISMATCH:\n{marketplace_mismatch_str}\n</yellow>"
            )
            logger.info("Did you forget to specify the marketplace?")

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
                f"<yellow>NOT UPLOADED DUE TO VERSION MISMATCH:\n{version_mismatch_str}\n</yellow>"
            )

        if self.failed_parsing:
            failed_parsing_str = tabulate(
                ((path.name, path, reason) for path, reason in self.failed_parsing),
                headers=("FILE_NAME", "PATH", "REASON"),
                tablefmt="fancy_grid",
            )
            logger.info(f"<red>FAILED PARSING CONTENT:\n{failed_parsing_str}</red>")

        if self._failed_upload_content_items or self._failed_upload_zips:
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
                                for item in self._failed_upload_zips
                            )
                        ),
                    )
                ),
                headers=["NAME", "TYPE", "ERROR"],
                tablefmt="fancy_grid",
            )
            logger.info(f"<red>FAILED UPLOADS:\n{failed_upload_str}\n</red>")


class ConfigFileParser:
    def __init__(self, path: Path):
        self.path = path
        self.content = get_file(self.path, raise_on_error=True)

        self.custom_packs_paths: Tuple[Path, ...] = tuple(
            Path(pack["url"]) for pack in self.content.get("custom_packs", ())
        )


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
            logger.info(f"\n<green>File: {file_id} was detached</green>")
        except Exception as e:
            raise Exception(f"Exception raised when fetching custom content:\n{e}")

    def extract_items_from_dir(self):
        detach_files_list: list = []

        all_files = glob.glob(f"{self.file_path}/**/*", recursive=True)
        for file_path in all_files:
            if Path(file_path).is_file() and self.is_valid_file_for_detach(file_path):
                file_type = self.find_item_type_to_detach(file_path)
                file_data = get_file(file_path)
                file_id = file_data.get("id", "")
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
        self.find_item_type_to_detach(self.file_path)
        file_data = get_file(self.file_path)
        return file_data.get("id")

    def detach(self, upload_file: bool = False) -> List[str]:
        detach_files_list: list = []
        if os.path.isdir(self.file_path):
            detach_files_list = self.extract_items_from_dir()
            for file in detach_files_list:
                self.detach_item(file.get("file_id"), file_path=file.get("file_path"))
                if upload_file:
                    Uploader(
                        input=(
                            Path(raw_file_path)
                            if (raw_file_path := file.get("file_path")) is not None
                            else None
                        ),
                        marketplace=self.marketplace,
                    ).upload()

        elif Path(self.file_path).is_file():
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
            logger.debug(f"\n<green>{item_type}: {item_id} was reattached</green>")
        except Exception as e:
            raise Exception(f"Exception raised when fetching custom content:\n{e}")

    def reattach(self, detached_files_ids=None):
        if not self.file_path and detached_files_ids:
            all_files: dict = self.download_all_detach_supported_items()
            for item_type, item_list in all_files.items():
                for item in item_list:
                    detached = item.get("detached", "")
                    if not detached or detached == "false":
                        continue
                    item_id = item.get("id")
                    if item_id and item_id not in detached_files_ids:
                        self.reattach_item(item_id, item_type)


def is_uploadable_dir(path: Path) -> bool:
    if not path.is_dir():
        raise ValueError(f"{path} is not a directory")

    return path.name in CONTENT_ENTITIES_DIRS or (
        path.name in {INTEGRATIONS_DIR, SCRIPTS_DIR}
        and path.parent.name in CONTENT_ENTITIES_DIRS
    )


def parse_uploaded_successfully(
    content_item: Union[Pack, ContentItem], zip: bool, tpb: bool
) -> Iterable[Union[Pack, ContentItem]]:
    # packs uploaded unzipped are uploaded item by item, we have to extract the item details here
    if isinstance(content_item, Pack) and not zip:
        return iter(
            filter(
                lambda content_item: (
                    content_item.content_type not in CONTENT_TYPES_EXCLUDED_FROM_UPLOAD
                    or (tpb and content_item.content_type == ContentType.TEST_PLAYBOOK)
                ),
                content_item.content_items,
            )
        )

    return (content_item,)
