import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from demisto_sdk.commands.common.constants import (
    GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH,
    MARKDOWN_IMAGE_LINK_REGEX,
    MARKDOWN_IMAGES_ARTIFACT_FILE_NAME,
    SERVER_API_TO_STORAGE,
    ImagesFolderNames,
    MarketplaceVersions,
    MarketplaceVersionToMarketplaceName,
)
from demisto_sdk.commands.common.logger import logger
from demisto_sdk.commands.common.tools import get_file


def replace_markdown_urls_and_upload_to_artifacts(
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
    Returns:
        - A dict in the form of {pack_name: [images_data]} or empty dict if no images urls were found in the README
    """
    readme_images_storage_data = (
        collect_images_from_markdown_and_replace_with_storage_path(
            markdown_path, pack_name, marketplace, file_type
        )
    )
    # no external image urls were found in the readme file
    if not readme_images_storage_data[pack_name]:
        logger.debug(f"no image links were found in {pack_name} readme file")
        return {}

    upload_markdown_images_to_artifacts(readme_images_storage_data, pack_name)
    logger.info(f"{readme_images_storage_data=}")
    return readme_images_storage_data


def collect_images_from_markdown_and_replace_with_storage_path(
    markdown_path: Path,
    pack_name: str,
    marketplace: MarketplaceVersions,
    file_type: ImagesFolderNames,
) -> dict:
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
    google_api_readme_images_url = (
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
        to_replace = google_api_readme_images_url

    urls_list = []

    with open(markdown_path, "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if res := re.search(MARKDOWN_IMAGE_LINK_REGEX, line):
            url = res["url"]
            parse_url = urlparse(url)
            url_path = Path(parse_url.path)
            image_name = url_path.name
            new_replace_url = os.path.join(to_replace, file_type.value, image_name)
            lines[i] = line.replace(url, new_replace_url)
            logger.debug(f"Replacing {url=} with new url {new_replace_url=}")

            image_gcp_path = (
                f"{google_api_readme_images_url}/{file_type.value}/{image_name}"
            )
            relative_image_path = f"{pack_name}/{file_type.value}/{image_name}"
            urls_list.append(
                {
                    "original_readme_url": url,
                    "final_dst_image_path": image_gcp_path,
                    "relative_image_path": relative_image_path,
                    "image_name": image_name,
                }
            )

    with open(markdown_path, "w") as file:
        file.writelines(lines)

    return {pack_name: {file_type.value: urls_list}}


def upload_markdown_images_to_artifacts(images_dict: dict, pack_name: str):
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        artifacts_readme_images_path = Path(
            f"{artifacts_folder}/{MARKDOWN_IMAGES_ARTIFACT_FILE_NAME}"
        )
        if not artifacts_readme_images_path.exists():
            with open(artifacts_readme_images_path, "w") as f:
                # If this is the first pack init the file with an empty dict.
                json.dump({}, f)

        markdown_images_data_dict = get_file(
            artifacts_readme_images_path, type_of_file="json"
        )
        if pack_name in markdown_images_data_dict:
            markdown_images_data_dict[pack_name].update(images_dict[pack_name])
        else:
            markdown_images_data_dict.update(images_dict)

        with open(artifacts_readme_images_path, "w") as fp:
            json.dump(markdown_images_data_dict, fp, indent=4)
