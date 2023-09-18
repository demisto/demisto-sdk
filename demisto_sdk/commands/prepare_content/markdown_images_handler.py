import os
import re
from pathlib import Path
from urllib.parse import urlparse

from demisto_sdk.commands.common.constants import (
    GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH,
    MARKDOWN_IMAGES_ARTIFACT_FILE_NAME,
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
    write_dict,
)

json = JSON_Handler()


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
    urls_list = collect_images_from_markdown_and_replace_with_storage_path(
        markdown_path, pack_name, marketplace, file_type
    )
    # no external image urls were found in the readme file
    if not urls_list:
        logger.debug(f"no image links were found in {pack_name} readme file")
        return {}

    save_to_artifact = {pack_name: {file_type: urls_list}}

    upload_markdown_images_to_artifacts(save_to_artifact, pack_name, file_type)
    logger.debug(f"{save_to_artifact=}")
    return save_to_artifact


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


def upload_markdown_images_to_artifacts(
    images_dict: dict, pack_name: str, file_type: ImagesFolderNames
):
    if (artifacts_folder := os.getenv("ARTIFACTS_FOLDER")) and Path(
        artifacts_folder
    ).exists():
        artifacts_markdown_images_path = Path(
            f"{artifacts_folder}/{MARKDOWN_IMAGES_ARTIFACT_FILE_NAME}"
        )
        if not artifacts_markdown_images_path.exists():
            with open(artifacts_markdown_images_path, "w") as f:
                # If this is the first pack init the file with an empty dict.
                json.dump({}, f)

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
