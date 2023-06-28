import os
import re
from pathlib import Path
from urllib.parse import urlparse

from demisto_sdk.commands.common.constants import (
    GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH,
    README_IMAGES,
    MarketplaceVersions,
    MarketplaceVersionToMarketplaceName,
)
from demisto_sdk.commands.common.logger import logger


def replace_readme_urls(
    pack_readme_path: Path, marketplace: MarketplaceVersions, pack_name: str
) -> dict:
    """
    This function goes over the pack readme.md file and by the marketplace value.
    replaces the images url to the appropriate images urls.
    Args:
        pack_readme_path (Path): The path of the pack readme file
        marketplace (MarketplaceVersions): The marketplace version
        pack_name (str): The pack name
    Returns:
        - A dict in the form of {pack_name: [images_data]} or empty dict if no images urls were found in the README
    """
    readme_images_storage_data = (
        collect_images_from_readme_and_replace_with_storage_path(
            pack_readme_path, pack_name, marketplace=marketplace
        )
    )
    # no external image urls were found in the readme file
    if not readme_images_storage_data:
        logger.debug(f"no image links were found in {pack_name} readme file")
        return {}

    logger.info(f"{readme_images_storage_data=}")
    return readme_images_storage_data


def collect_images_from_readme_and_replace_with_storage_path(
    pack_readme_path: Path, pack_name: str, marketplace: MarketplaceVersions
) -> dict:
    """
    Replaces inplace all images links in the pack README.md with their new gcs location

    Args:
        pack_readme_path (str): A path to the pack README file.
        gcs_pack_path (str): A path to the pack in gcs
        marketplace (str): The marketplace this pack is going to be uploaded to.

    Returns:
        A dict of the pack name and all the image urls found in the README.md file with all related data
        (original_url, new_gcs_path, image_name)
    """
    google_api_readme_images_url = (
        f"{GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH}/{MarketplaceVersionToMarketplaceName.get(marketplace)}"
        f"/content/packs/{pack_name}"
    )
    if marketplace in [
        MarketplaceVersions.XSOAR_SAAS,
        MarketplaceVersions.MarketplaceV2,
    ]:
        to_replace = f"api/marketplace/file?name=content/packs/{pack_name}"
    else:
        to_replace = google_api_readme_images_url

    url_regex = r"(\!\[.*?\])\((?P<url>[a-zA-Z_/\.0-9\- :%]*?)\)((].*)?)"
    urls_list = []

    with open(pack_readme_path, "r") as file:
        lines = file.readlines()

    for i, line in enumerate(lines):
        if res := re.search(url_regex, line):
            url = res["url"]
            parse_url = urlparse(url)
            url_path = Path(parse_url.path)
            image_name = url_path.name
            new_replace_url = os.path.join(to_replace, README_IMAGES, image_name)
            lines[i] = line.replace(url, new_replace_url)
            logger.debug(f"Replacing {url=} with new url {new_replace_url=}")

            image_gcp_path = (
                f"{google_api_readme_images_url}/{README_IMAGES}/{image_name}"
            )
            urls_list.append(
                {
                    "original_read_me_url": url,
                    "new_gcs_image_path": image_gcp_path,
                    "image_name": image_name,
                }
            )

    with open(pack_readme_path, "w") as file:
        file.writelines(lines)

    return {pack_name: urls_list}
