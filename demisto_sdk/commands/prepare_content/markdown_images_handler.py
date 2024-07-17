import os
import re
from pathlib import Path
from typing import List, Tuple
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
    get_file,
    run_sync,
    write_dict,
)

json = JSON_Handler()


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


def collect_images_from_markdown_and_replace_with_storage_path(
    markdown_path: Path,
    pack_name: str,
    marketplace: MarketplaceVersions,
    file_type: ImagesFolderNames,
) -> list:
    """
    Replaces inplace all images links in the pack README.md with their new gcs location

    Args:
        markdown_path (str): A path to the pack README file.
        pack_name (str): A string of the pack name.
        marketplace (str): The marketplace this pack is going to be uploaded to.

    Returns:
        A dict of the pack name and all the image urls found in the README.md file with all related data
        (original_url - The original url as found in the README.md file.
         final_dst_image_path - The destination where the image will be stored on gcp.
         relative_image_path - The relative path (from the pack name root) in the gcp.
         image_name - the image name)
    """
    google_api_markdown_images_url = (
        f"{GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH}/{MarketplaceVersionToMarketplaceName.get(marketplace)}"
        f"/content/packs/{pack_name}"
    )
    if marketplace in [
        MarketplaceVersions.XSOAR_SAAS,
        MarketplaceVersions.MarketplaceV2,
        MarketplaceVersions.XPANSE,
    ]:
        to_replace = f"{SERVER_API_TO_STORAGE}/{pack_name}"
    else:
        to_replace = google_api_markdown_images_url

    urls_list = []

    with open(markdown_path, "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if res := re.search(URL_IMAGE_LINK_REGEX, line):
            url = res["url"]
            parse_url = urlparse(url)
            url_path = Path(parse_url.path)
            image_name = url_path.name
            new_replace_url = os.path.join(to_replace, file_type.value, image_name)
            lines[i] = line.replace(url, new_replace_url)
            logger.debug(f"Replacing {url=} with new url {new_replace_url=}")

            image_gcp_path = (
                f"{google_api_markdown_images_url}/{file_type.value}/{image_name}"
            )
            relative_image_path = f"{pack_name}/{file_type.value}/{image_name}"
            urls_list.append(
                {
                    "original_markdown_url": url,
                    "final_dst_image_path": image_gcp_path,
                    "relative_image_path": relative_image_path,
                    "image_name": image_name,
                }
            )

    with open(markdown_path, "w") as file:
        file.writelines(lines)

    return urls_list


def init_json_file(markdown_images_file_name: str):
    """Initialize a json file at with the given file name if doesn't exist.

    Args:
        markdown_images_file_name (str): The file name to create.
    """
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        artifacts_markdown_images_path = Path(
            f"{artifacts_folder}/{markdown_images_file_name}"
        )
        if not artifacts_markdown_images_path.exists():
            with open(artifacts_markdown_images_path, "w") as f:
                # If this is the first pack init the file with an empty dict.
                json.dump({}, f)


def update_markdown_images_file_links(
    images_dict: dict,
    pack_name: str,
    file_type: ImagesFolderNames,
    markdown_images_file_name: str = MARKDOWN_IMAGES_ARTIFACT_FILE_NAME,
):
    """Update the markdown_images.json file containing all the modified links.

    Args:
        images_dict (dict): The dict contains all the images info for the current pack.
        pack_name (str): The name of the pack to update.
        file_type (ImagesFolderNames): The markdown file the pics was obtained from.
        markdown_images_file_name (str): The file to write the results into. The default is markdown_images.json
    """
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        artifacts_markdown_images_path = Path(
            f"{artifacts_folder}/{markdown_images_file_name}"
        )

        markdown_images_data_dict = get_file(
            artifacts_markdown_images_path, raise_on_error=True
        )
        if pack_name in markdown_images_data_dict:
            integration_desc = ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value
            if (
                file_type == ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES
                and markdown_images_data_dict.get(pack_name, {}).get(
                    integration_desc, {}
                )
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

        write_dict(
            artifacts_markdown_images_path,
            data=markdown_images_data_dict,
            indent=4,
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
        markdown_path (str): A path to the pack README file.
        pack_name (str): A string of the pack name.
        marketplace (str): The marketplace this pack is going to be uploaded to.

    Returns:
        A dict of the pack name and all the image urls found in the README.md file with all related data
        (original_url - The original url as found in the README.md file.
         final_dst_image_path - The destination where the image will be stored on gcp.
         relative_image_path - The relative path (from the pack name root) in the gcp.
         image_name - the image name)
    """
    google_api_markdown_images_url = (
        f"{GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH}/{MarketplaceVersionToMarketplaceName.get(marketplace)}"
        f"/content/packs/{pack_name}"
    )
    if marketplace in [
        MarketplaceVersions.XSOAR_SAAS,
        MarketplaceVersions.MarketplaceV2,
        MarketplaceVersions.XPANSE,
    ]:
        to_replace = f"{SERVER_API_TO_STORAGE}/{pack_name}"
    else:
        to_replace = google_api_markdown_images_url

    images_list = []

    with open(markdown_path, "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if res := re.search(DOC_FILE_IMAGE_REGEX, line):
            rel_path = res.group()
            image_path = Path(rel_path)
            image_name = image_path.name
            new_replace_url = os.path.join(to_replace, file_type.value, image_name)
            lines[i] = line.replace(rel_path, new_replace_url)
            logger.debug(f"Replacing {rel_path=} with new url {new_replace_url=}")

            image_gcp_path = (
                f"{google_api_markdown_images_url}/{file_type.value}/{image_name}"
            )
            relative_image_path = f"{pack_name}/{file_type.value}/{image_name}"
            images_list.append(
                {
                    "final_dst_image_path": image_gcp_path,
                    "relative_image_path": relative_image_path,
                    "image_name": image_name,
                }
            )

    with open(markdown_path, "w") as file:
        file.writelines(lines)

    return images_list
