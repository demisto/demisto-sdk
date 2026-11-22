import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple
from urllib.parse import urlparse

from demisto_sdk.commands.common.constants import (
    DOC_FILE_IMAGE_REGEX,
    GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH,
    MARKDOWN_IMAGES_ARTIFACT_FILE_NAME,
    MARKDOWN_RELATIVE_PATH_IMAGES_ARTIFACT_FILE_NAME,
    SERVER_API_TO_STORAGE,
    URL_IMAGE_LINK_REGEX,
    ImagesFolderNames,
    MarketplaceVersions,
    MarketplaceVersionToMarketplaceName,
)
from demisto_sdk.commands.common.handlers import JSON_Handler
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import (
    run_sync,
    write_dict,
)

json = JSON_Handler()

# One recorded ``update_markdown_images_file_links`` call, as plain picklable data:
# (markdown_images_file_name, images_dict, pack_name, file_type value).
MarkdownImagesUpdate = Tuple[str, dict, str, str]


class MarkdownImagesCollector:
    """Records markdown images file updates in memory instead of writing the shared JSON files.

    Used during a content dump: workers record, export the records as plain data, and the parent
    merges the exports in the serial dump order and writes each file once (``write_files``).
    Replaying the records in that order reproduces the serial read-modify-write output byte for byte.
    """

    def __init__(self) -> None:
        self.initialized_file_names: List[str] = []
        self.updates: List[MarkdownImagesUpdate] = []

    def record_init(self, markdown_images_file_name: str) -> None:
        if markdown_images_file_name not in self.initialized_file_names:
            self.initialized_file_names.append(markdown_images_file_name)

    def record_update(
        self,
        images_dict: dict,
        pack_name: str,
        file_type: ImagesFolderNames,
        markdown_images_file_name: str,
    ) -> None:
        # A JSON round trip, as in the serial write-then-read: plain types, and no aliasing with the caller's dict.
        normalized_images_dict = json.loads(json.dumps(images_dict))
        self.updates.append(
            (
                markdown_images_file_name,
                normalized_images_dict,
                pack_name,
                ImagesFolderNames(file_type).value,
            )
        )

    def export(self) -> Dict[str, Any]:
        """The recorded data as plain picklable data, e.g. to return it from a forked worker."""
        return {
            "initialized_file_names": list(self.initialized_file_names),
            "updates": list(self.updates),
        }

    def merge(self, exported_batches: Iterable[Dict[str, Any]]) -> None:
        """Append exported batches, in the given order (the caller passes the serial dump order)."""
        for exported_batch in exported_batches:
            for markdown_images_file_name in exported_batch["initialized_file_names"]:
                self.record_init(markdown_images_file_name)
            self.updates.extend(
                (file_name, images_dict, pack_name, file_type)
                for file_name, images_dict, pack_name, file_type in exported_batch[
                    "updates"
                ]
            )

    def write_files(self) -> None:
        """Write every recorded file once, under its lock, as the serial path would have left it.

        A recorded init creates the file with ``{}`` if it does not exist (as ``init_json_file``).
        Then the file is read once (pre-existing content included), the file's updates are applied
        in recording order with the same merge rule, and the result is written once with the same
        serialization (``write_dict(..., indent=4)``).
        """
        file_names = set(self.initialized_file_names)
        file_names.update(update[0] for update in self.updates)
        for markdown_images_file_name in sorted(file_names):
            file_updates = [
                (images_dict, pack_name, ImagesFolderNames(file_type))
                for file_name, images_dict, pack_name, file_type in self.updates
                if file_name == markdown_images_file_name
            ]
            _run_with_file_lock(
                markdown_images_file_name,
                _write_collected_file,
                {
                    "markdown_images_file_name": markdown_images_file_name,
                    "should_init": markdown_images_file_name
                    in self.initialized_file_names,
                    "file_updates": file_updates,
                },
            )


_ACTIVE_MARKDOWN_IMAGES_COLLECTOR: ContextVar[Optional[MarkdownImagesCollector]] = (
    ContextVar("active_markdown_images_collector", default=None)
)


def get_active_markdown_images_collector() -> Optional[MarkdownImagesCollector]:
    return _ACTIVE_MARKDOWN_IMAGES_COLLECTOR.get()


@contextmanager
def collect_markdown_images(
    collector: Optional[MarkdownImagesCollector] = None,
) -> Iterator[MarkdownImagesCollector]:
    """While active, markdown images file inits and updates are recorded in ``collector`` instead of written."""
    if collector is None:
        collector = MarkdownImagesCollector()
    token = _ACTIVE_MARKDOWN_IMAGES_COLLECTOR.set(collector)
    try:
        yield collector
    finally:
        _ACTIVE_MARKDOWN_IMAGES_COLLECTOR.reset(token)


def _get_artifacts_file_path(markdown_images_file_name: str) -> Optional[Path]:
    """``$ARTIFACTS_FOLDER/<file name>``, or None when ``ARTIFACTS_FOLDER`` is unset or missing."""
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        return Path(f"{artifacts_folder}/{markdown_images_file_name}")
    return None


def _run_with_file_lock(
    markdown_images_file_name: str, exclusive_function, exclusive_function_kwargs: dict
) -> None:
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        run_sync(
            f"{artifacts_folder}/{markdown_images_file_name.replace('json', 'lock')}",
            exclusive_function,
            exclusive_function_kwargs,
        )


def _init_json_file_on_disk(markdown_images_file_name: str) -> None:
    artifacts_markdown_images_path = _get_artifacts_file_path(markdown_images_file_name)
    if artifacts_markdown_images_path and not artifacts_markdown_images_path.exists():
        with open(artifacts_markdown_images_path, "w") as f:
            # If this is the first pack init the file with an empty dict.
            json.dump({}, f)


def _apply_markdown_images_update(
    markdown_images_data_dict: dict,
    images_dict: dict,
    pack_name: str,
    file_type: ImagesFolderNames,
) -> None:
    """Merge one pack's images dict into the file data, in place (the single merge rule)."""
    if pack_name in markdown_images_data_dict:
        integration_desc = ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value
        if (
            file_type == ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES
            and markdown_images_data_dict.get(pack_name, {}).get(integration_desc, {})
        ):
            # There is already an entry for the integration_description_images.
            markdown_images_data_dict[pack_name][integration_desc].append(
                images_dict[pack_name][integration_desc]
            )
        else:
            # No entry for the readme images of the integration_description_images.
            markdown_images_data_dict[pack_name].update(images_dict[pack_name])
    else:
        markdown_images_data_dict.update(images_dict)


def _apply_updates_on_disk(
    markdown_images_file_name: str,
    file_updates: List[Tuple[dict, str, ImagesFolderNames]],
) -> None:
    """Read the file once, apply ``file_updates`` in order, and write it once."""
    artifacts_markdown_images_path = _get_artifacts_file_path(markdown_images_file_name)
    if not artifacts_markdown_images_path or not file_updates:
        return
    # Read the file directly (not through the cached ``get_file``): this is a
    # read-modify-write under a cross-process lock, so a cached read could be
    # stale and overwrite entries written by another process.
    markdown_images_data_dict = json.loads(
        artifacts_markdown_images_path.read_text() or "{}"
    )
    for images_dict, pack_name, file_type in file_updates:
        # A copy, so the merged data never aliases (and later mutates) a caller's or a recorded dict.
        # The serial path gets the same isolation from writing and re-reading the file between updates.
        _apply_markdown_images_update(
            markdown_images_data_dict, deepcopy(images_dict), pack_name, file_type
        )
    write_dict(
        artifacts_markdown_images_path,
        data=markdown_images_data_dict,
        indent=4,
    )


def _write_collected_file(
    markdown_images_file_name: str,
    should_init: bool,
    file_updates: List[Tuple[dict, str, ImagesFolderNames]],
) -> None:
    if should_init:
        _init_json_file_on_disk(markdown_images_file_name)
    _apply_updates_on_disk(markdown_images_file_name, file_updates)


def update_markdown_images_with_urls_and_rel_paths(
    markdown_path: Path,
    marketplace: MarketplaceVersions,
    pack_name: str,
    file_type: ImagesFolderNames,
) -> Tuple[dict, dict]:
    urls_dict = replace_markdown_urls_and_update_markdown_images(
        markdown_path, marketplace, pack_name, file_type
    )
    rel_paths_dict = replace_markdown_rel_paths_and_upload_to_artifacts(
        markdown_path, marketplace, pack_name, file_type
    )
    return (urls_dict, rel_paths_dict)


def safe_init_json_file(file_path: str):
    """Calling the init_json_file function using the synced function.

    Args:
        file_path (str): The json file path to init
    """
    if collector := get_active_markdown_images_collector():
        collector.record_init(file_path)
        return
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        lock_file_path = f"{artifacts_folder}/{file_path.replace('json', 'lock')}"
        run_sync(
            lock_file_path,
            init_json_file,
            {"markdown_images_file_name": file_path},
        )


def replace_markdown_urls_and_update_markdown_images(
    markdown_path: Path,
    marketplace: MarketplaceVersions,
    pack_name: str,
    file_type: ImagesFolderNames,
) -> dict:
    """
    This function goes over the pack readme.md file and by the marketplace value.
    replaces the images url to the appropriate images urls.
    Args:
        markdown_path (Path): The path of the pack readme file
        marketplace (MarketplaceVersions): The marketplace version
        pack_name (str): The pack name
        file_type (ImagesFolderNames): The type of file to get the info from (pack readme of integration description).
    Returns:
        - A dict in the form of {pack_name: [images_data]} or empty dict if no images urls were found in the README
    """
    safe_init_json_file(MARKDOWN_IMAGES_ARTIFACT_FILE_NAME)
    urls_list = collect_images_from_markdown_and_replace_with_storage_path(
        markdown_path, pack_name, marketplace, file_type
    )
    # no external image urls were found in the readme file
    if not urls_list:
        logger.debug(f"no image links were found in {pack_name} readme file.")
        return {}

    save_to_artifact = {pack_name: {file_type: urls_list}}
    safe_update_markdown_images_file_links(
        save_to_artifact, pack_name, file_type, MARKDOWN_IMAGES_ARTIFACT_FILE_NAME
    )

    logger.debug(f"returning the following urls to artifacts.\n{save_to_artifact=}")
    return save_to_artifact


def replace_markdown_rel_paths_and_upload_to_artifacts(
    markdown_path: Path,
    marketplace: MarketplaceVersions,
    pack_name: str,
    file_type: ImagesFolderNames,
) -> dict:
    """
    This function goes over the pack readme.md file and by the marketplace value.
    replaces the images relative paths to the appropriate images urls.
    Args:
        markdown_path (Path): The path of the pack readme file
        marketplace (MarketplaceVersions): The marketplace version
        pack_name (str): The pack name
        file_type (ImagesFolderNames): The type of file to get the info from (pack readme of integration description).
    Returns:
        - A dict in the form of {pack_name: [images_data]} or empty dict if no images relative paths were found in the README
    """
    safe_init_json_file(MARKDOWN_RELATIVE_PATH_IMAGES_ARTIFACT_FILE_NAME)
    rel_paths_list = (
        collect_images_relative_paths_from_markdown_and_replace_with_storage_path(
            markdown_path, pack_name, marketplace, file_type
        )
    )
    # no external image urls were found in the readme file
    if not rel_paths_list:
        logger.debug(f"no image relative paths were found in {pack_name} readme file.")
        return {}

    save_to_artifact = {pack_name: {file_type: rel_paths_list}}
    safe_update_markdown_images_file_links(
        save_to_artifact,
        pack_name,
        file_type,
        MARKDOWN_RELATIVE_PATH_IMAGES_ARTIFACT_FILE_NAME,
    )

    logger.debug(f"Saved the following rel_paths to artifacts.\n{save_to_artifact=}")
    return save_to_artifact


def safe_update_markdown_images_file_links(
    images_dict, pack_name, file_type, image_file_path
):
    """Calling the update_markdown_images_file_links function using the synced function.

    Args:
        images_dict (dict): The dict contains all the images info for the current pack.
        pack_name (str): The name of the pack to update.
        file_type (ImagesFolderNames): The markdown file the pics was obtained from.
        image_file_path (str): The json file path to update
    """
    if collector := get_active_markdown_images_collector():
        collector.record_update(images_dict, pack_name, file_type, image_file_path)
        return
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        run_sync(
            f"{artifacts_folder}/{image_file_path.replace('json', 'lock')}",
            update_markdown_images_file_links,
            {
                "images_dict": images_dict,
                "pack_name": pack_name,
                "file_type": file_type,
                "markdown_images_file_name": image_file_path,
            },
        )


def init_json_file(markdown_images_file_name: str):
    """Initialize a json file at with the given file name if doesn't exist.

    With an active ``MarkdownImagesCollector``, the init is recorded instead (done by ``write_files``).

    Args:
        markdown_images_file_name (str): The file name to create.
    """
    if collector := get_active_markdown_images_collector():
        collector.record_init(markdown_images_file_name)
        return
    _init_json_file_on_disk(markdown_images_file_name)


def update_markdown_images_file_links(
    images_dict: dict,
    pack_name: str,
    file_type: ImagesFolderNames,
    markdown_images_file_name: str = MARKDOWN_IMAGES_ARTIFACT_FILE_NAME,
):
    """Update the markdown_images.json file containing all the modified links.

    With an active ``MarkdownImagesCollector``, the update is recorded instead of written.

    Args:
        images_dict (dict): The dict contains all the images info for the current pack.
        pack_name (str): The name of the pack to update.
        file_type (ImagesFolderNames): The markdown file the pics was obtained from.
        markdown_images_file_name (str): The file to write the results into. The default is markdown_images.json
    """
    if collector := get_active_markdown_images_collector():
        collector.record_update(
            images_dict, pack_name, file_type, markdown_images_file_name
        )
        return
    _apply_updates_on_disk(
        markdown_images_file_name, [(images_dict, pack_name, file_type)]
    )


def process_markdown_images(
    markdown_path: Path,
    pack_name: str,
    marketplace: MarketplaceVersions,
    file_type: ImagesFolderNames,
    is_url: bool,
) -> List[dict]:
    """
    Generic function to process images in markdown and replace with storage path

    Args:
        markdown_path (Path): A path to the pack README file.
        pack_name (str): A string of the pack name.
        marketplace (MarketplaceVersions): The marketplace this pack is going to be uploaded to.
        file_type (ImagesFolderNames): The type of file to process.
        is_url (bool): True if processing URL images, False if processing relative paths

    Returns:
        A list of dicts with all the image data found in the README.md file
    """
    bucket_path = MarketplaceVersionToMarketplaceName.get(marketplace)
    if bucket_path and marketplace == MarketplaceVersions.PLATFORM.value:
        bucket_path += "/april-content"  # CIAC-13208

    google_api_markdown_images_url = f"{GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH}/{bucket_path}/content/packs/{pack_name}"

    if marketplace in [
        MarketplaceVersions.XSOAR_SAAS,
        MarketplaceVersions.MarketplaceV2,
        MarketplaceVersions.XPANSE,
        MarketplaceVersions.PLATFORM,
    ]:
        to_replace = f"{SERVER_API_TO_STORAGE}/{pack_name}"
    else:
        to_replace = google_api_markdown_images_url

    images_list = []

    with open(markdown_path, "r") as file:
        lines = file.readlines()

    pattern = URL_IMAGE_LINK_REGEX if is_url else DOC_FILE_IMAGE_REGEX

    for i, line in enumerate(lines):
        if res := re.search(pattern, line):
            # Extract the path based on the type of image reference
            if is_url:
                original_path = res["url"]
                parse_url = urlparse(original_path)
                path_obj = Path(parse_url.path)
            else:
                original_path = res.group()
                path_obj = Path(original_path)

            image_name = path_obj.name
            new_replace_url = os.path.join(to_replace, file_type.value, image_name)
            lines[i] = line.replace(original_path, new_replace_url)
            logger.debug(f"Replacing {original_path=} with new url {new_replace_url=}")

            image_gcp_path = (
                f"{google_api_markdown_images_url}/{file_type.value}/{image_name}"
            )
            relative_image_path = f"{pack_name}/{file_type.value}/{image_name}"

            image_data = {
                "final_dst_image_path": image_gcp_path,
                "relative_image_path": relative_image_path,
                "image_name": image_name,
            }

            if is_url:
                image_data["original_markdown_url"] = original_path

            images_list.append(image_data)

    with open(markdown_path, "w") as file:
        file.writelines(lines)

    return images_list


def collect_images_from_markdown_and_replace_with_storage_path(
    markdown_path: Path,
    pack_name: str,
    marketplace: MarketplaceVersions,
    file_type: ImagesFolderNames,
) -> list:
    """
    Replaces inplace all images links in the pack README.md with their new gcs location

    Args:
        markdown_path (Path): A path to the pack README file.
        pack_name (str): A string of the pack name.
        marketplace (MarketplaceVersions): The marketplace this pack is going to be uploaded to.
        file_type (ImagesFolderNames): The type of file to process.

    Returns:
        A list of dicts with all the image URLs found in the README.md file with all related data
    """
    return process_markdown_images(
        markdown_path=markdown_path,
        pack_name=pack_name,
        marketplace=marketplace,
        file_type=file_type,
        is_url=True,
    )


def collect_images_relative_paths_from_markdown_and_replace_with_storage_path(
    markdown_path: Path,
    pack_name: str,
    marketplace: MarketplaceVersions,
    file_type: ImagesFolderNames,
) -> List[dict]:
    """
    Replaces inplace all images relative paths in the pack README.md with their new gcs location

    Args:
        markdown_path (Path): A path to the pack README file.
        pack_name (str): A string of the pack name.
        marketplace (MarketplaceVersions): The marketplace this pack is going to be uploaded to.
        file_type (ImagesFolderNames): The type of file to process.

    Returns:
        A list of dicts with all the relative image paths found in the README.md file with all related data
    """
    return process_markdown_images(
        markdown_path=markdown_path,
        pack_name=pack_name,
        marketplace=marketplace,
        file_type=file_type,
        is_url=False,
    )
