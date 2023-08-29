import os
import re
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from demisto_sdk.commands.common.constants import (
    GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH,
    MARKDOWN_IMAGES_ARTIFACT_FILE_NAME,
    SERVER_API_TO_STORAGE,
    URL_IMAGE_LINK_REGEX,
    ImagesFolderNames,
    MarketplaceVersions,
    MarketplaceVersionToMarketplaceName,
)
from demisto_sdk.commands.common.tools import get_file
from demisto_sdk.commands.prepare_content import markdown_images_handler
from demisto_sdk.commands.prepare_content.markdown_images_handler import (
    upload_markdown_images_to_artifacts,
)

expected_urls_ret = [
    {
        "original_markdown_url": "https://raw.githubusercontent.com/crestdatasystems/content/"
        "4f707f8922d7ef1fe234a194dcc6fa73f96a4a87/Packs/Lansweeper/doc_files/"
        "Retrieve_Asset_Details_-_Lansweeper.png",
        "final_dst_image_path": f"{GOOGLE_CLOUD_STORAGE_PUBLIC_BASE_PATH}/"
        f"{MarketplaceVersionToMarketplaceName.get(MarketplaceVersions.XSOAR)}/"
        f"content/packs/test_pack/{ImagesFolderNames.README_IMAGES.value}/Retrieve_Asset_Details_-_Lansweeper.png",
        "relative_image_path": f"test_pack/{ImagesFolderNames.README_IMAGES.value}/Retrieve_Asset_Details_-_Lansweeper.png",
        "image_name": "Retrieve_Asset_Details_-_Lansweeper.png",
    }
]


@pytest.mark.parametrize(
    "marketplace, expected_res", [(MarketplaceVersions.XSOAR, expected_urls_ret)]
)
def test_collect_images_from_markdown_and_replace_with_storage_path(
    marketplace, expected_res
):
    """
    Given:
        - A README.md file with external urls
    When:
        - uploading the pack images to gcs
    Then:
        - replace the readme images url with the new path to gcs return a list of all replaces urls.
    """
    readme_images_test_folder_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_data",
        "readme_images_test_data",
    )
    path_readme_to_replace_url = Path(
        readme_images_test_folder_path, "url_replace_README.md"
    )
    data = Path(
        os.path.join(readme_images_test_folder_path, "original_README.md")
    ).read_text()
    with open(path_readme_to_replace_url, "w") as to_replace:
        to_replace.write(data)

    ret = markdown_images_handler.collect_images_from_markdown_and_replace_with_storage_path(
        markdown_path=path_readme_to_replace_url,
        pack_name="test_pack",
        marketplace=marketplace,
        file_type=ImagesFolderNames.README_IMAGES,
    )

    assert ret == expected_res

    replaced = Path(path_readme_to_replace_url).read_text()
    expected = Path(
        os.path.join(readme_images_test_folder_path, "README_after_replace.md")
    ).read_text()
    assert replaced == expected


def test_replace_markdown_urls(mocker):
    """
    Given no urls were found in the pack readme return an empty dict.
    """
    mocker.patch.object(
        markdown_images_handler,
        "collect_images_from_markdown_and_replace_with_storage_path",
        return_value={},
    )
    assert (
        markdown_images_handler.replace_markdown_urls_and_upload_to_artifacts(
            Path("fake_path"),
            MarketplaceVersions.XSOAR,
            "test_pack",
            ImagesFolderNames.README_IMAGES,
        )
        == {}
    )


@pytest.mark.parametrize(
    "marketplace, expected_res",
    [
        (MarketplaceVersions.MarketplaceV2, True),
        (MarketplaceVersions.XPANSE, True),
        (MarketplaceVersions.XSOAR_SAAS, True),
        (MarketplaceVersions.XSOAR, False),
    ],
)
def test_collect_images_from_markdown_and_replace_with_storage_path_different_marketplaces(
    marketplace, expected_res
):
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w") as f:
        f.write(
            "![image](https://raw.githubusercontent.com/demisto/content/f808c78aa6c94a09450879c8702a1b7f023f1d4b/Packs/PrismaCloudCompute/doc_files/prisma_alert_raw_input.png)"
        )
        f.flush()
        markdown_images_handler.collect_images_from_markdown_and_replace_with_storage_path(
            Path(f.name), "test_pack", marketplace, ImagesFolderNames.README_IMAGES
        )
        res = Path(f.name).read_text()
        assert (SERVER_API_TO_STORAGE in res) == expected_res


@pytest.fixture
def image_data_one():
    return [
        {
            "original_markdown_url": "https://user-images.githubusercontent.com/49071222/72906531-0e452a00-3d3b-11ea-8703-8b97ddf30be0.png",
            "final_dst_image_path": "https://storage.googleapis.com/marketplace-saas-dist/content/packs/PrismaCloudCompute/readme_images/72906531-0e452a00-3d3b-11ea-8703-8b97ddf30be0.png",
            "relative_image_path": "PrismaCloudCompute/readme_images/72906531-0e452a00-3d3b-11ea-8703-8b97ddf30be0.png",
            "image_name": "72906531-0e452a00-3d3b-11ea-8703-8b97ddf30be0.png",
        },
        {
            "original_markdown_url": "https://raw.githubusercontent.com/demisto/content/f808c78aa6c94a09450879c8702a1b7f023f1d4b/Packs/PrismaCloudCompute/doc_files/prisma_alert_raw_input.png",
            "final_dst_image_path": "https://storage.googleapis.com/marketplace-saas-dist/content/packs/PrismaCloudCompute/readme_images/prisma_alert_raw_input.png",
            "relative_image_path": "PrismaCloudCompute/readme_images/prisma_alert_raw_input.png",
            "image_name": "prisma_alert_raw_input.png",
        },
        {
            "original_markdown_url": "https://raw.githubusercontent.com/demisto/content/f808c78aa6c94a09450879c8702a1b7f023f1d4b/Packs/PrismaCloudCompute/doc_files/prisma_alert_outputs.png",
            "final_dst_image_path": "https://storage.googleapis.com/marketplace-saas-dist/content/packs/PrismaCloudCompute/readme_images/prisma_alert_outputs.png",
            "relative_image_path": "PrismaCloudCompute/readme_images/prisma_alert_outputs.png",
            "image_name": "prisma_alert_outputs.png",
        },
        {
            "original_markdown_url": "https://raw.githubusercontent.com/demisto/content/f808c78aa6c94a09450879c8702a1b7f023f1d4b/Packs/PrismaCloudCompute/doc_files/prisma_instance.png",
            "final_dst_image_path": "https://storage.googleapis.com/marketplace-saas-dist/content/packs/PrismaCloudCompute/readme_images/prisma_instance.png",
            "relative_image_path": "PrismaCloudCompute/readme_images/prisma_instance.png",
            "image_name": "prisma_instance.png",
        },
    ]


@pytest.fixture
def image_data_two():
    return [
        {
            "original_markdown_url": "https://raw.githubusercontent.com/demisto/content/8895e8b967ee7d664276bd31df5af849e2c9a603/Packs/CVE_2022_30190/doc_files/CVE-2022-30190_-_MSDT_RCE.png",
            "final_dst_image_path": "https://storage.googleapis.com/marketplace-saas-dist/content/packs/CVE_2022_30190/readme_images/CVE-2022-30190_-_MSDT_RCE.png",
            "relative_image_path": "CVE_2022_30190/readme_images/CVE-2022-30190_-_MSDT_RCE.png",
            "image_name": "CVE-2022-30190_-_MSDT_RCE.png",
        }
    ]


def test_dump_same_pack_images_in_desc_and_readme(
    mocker, image_data_one, image_data_two
):
    """
    Given:
        - pack readmes with images and description with images for the same pack
    When:
        - After the readme images were parsed and data was collected for each url
    Then:
        - Validate that the data stored in the file that gathers all the pake readme
            images data is created succesfully.
    """
    pack_name = "PrismaCloudCompute"
    return_value1 = {pack_name: {ImagesFolderNames.README_IMAGES.value: image_data_one}}

    return_value2 = {
        pack_name: {
            ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value: image_data_two
        }
    }
    excepted_res = deepcopy(return_value1)
    excepted_res[pack_name].update(deepcopy(return_value2[pack_name]))
    with TemporaryDirectory() as artifact_dir:
        mocker.patch.object(os, "getenv", return_value=artifact_dir)
        upload_markdown_images_to_artifacts(
            return_value1, pack_name, ImagesFolderNames.README_IMAGES
        )
        upload_markdown_images_to_artifacts(
            return_value2, pack_name, ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES
        )
        res = get_file(f"{artifact_dir}/{MARKDOWN_IMAGES_ARTIFACT_FILE_NAME}")
    assert res == excepted_res


def test_dump_pack_readme(mocker, image_data_one, image_data_two):
    """
    Given:
        - pack readmes with images
    When:
        - After the readme images were parsed and data was collected for each url
    Then:
        - Validate that the data stored in the file that gathers all the pake readme
            images data is created succesfully.
    """
    return_value1 = {
        "PrismaCloudCompute": {ImagesFolderNames.README_IMAGES.value: image_data_one}
    }

    return_value2 = {
        "CVE_2022_30190": {
            ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value: image_data_two
        }
    }
    excepted_res = deepcopy(return_value1)
    excepted_res.update(deepcopy(return_value2))
    with TemporaryDirectory() as artifact_dir:
        mocker.patch.object(os, "getenv", return_value=artifact_dir)
        upload_markdown_images_to_artifacts(
            return_value1, "PrismaCloudCompute", ImagesFolderNames.README_IMAGES
        )
        upload_markdown_images_to_artifacts(
            return_value2,
            "CVE_2022_30190",
            ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES,
        )
        res = get_file(f"{artifact_dir}/{MARKDOWN_IMAGES_ARTIFACT_FILE_NAME}")
    assert res == excepted_res


def test_dump_more_than_one_description_file_one_empty(mocker, image_data_one):
    pack_name = "PrismaCloudCompute"
    return_value1 = {
        pack_name: {
            ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value: image_data_one
        }
    }

    return_value2: dict = {
        pack_name: {ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value: []}
    }
    excepted_res = deepcopy(return_value1)
    excepted_res[pack_name][
        ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value
    ].append(
        deepcopy(
            return_value2[pack_name][
                ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value
            ]
        )
    )
    with TemporaryDirectory() as artifact_dir:
        mocker.patch.object(os, "getenv", return_value=artifact_dir)
        upload_markdown_images_to_artifacts(
            return_value1, pack_name, ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES
        )
        upload_markdown_images_to_artifacts(
            return_value2, pack_name, ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES
        )
        res = get_file(f"{artifact_dir}/{MARKDOWN_IMAGES_ARTIFACT_FILE_NAME}")
    assert res == excepted_res


def test_dump_more_than_one_description_file(mocker, image_data_one, image_data_two):
    pack_name = "PrismaCloudCompute"
    return_value1 = {
        pack_name: {
            ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value: image_data_one
        }
    }

    return_value2: dict = {
        pack_name: {
            ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value: image_data_two
        }
    }
    excepted_res = deepcopy(return_value1)
    excepted_res[pack_name][
        ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value
    ].append(
        (
            deepcopy(
                return_value2[pack_name][
                    ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES.value
                ]
            )
        )
    )
    with TemporaryDirectory() as artifact_dir:
        mocker.patch.object(os, "getenv", return_value=artifact_dir)
        upload_markdown_images_to_artifacts(
            return_value1, pack_name, ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES
        )
        upload_markdown_images_to_artifacts(
            return_value2, pack_name, ImagesFolderNames.INTEGRATION_DESCRIPTION_IMAGES
        )
        res = get_file(f"{artifact_dir}/{MARKDOWN_IMAGES_ARTIFACT_FILE_NAME}")
    assert res == excepted_res


@pytest.mark.parametrize(
    "line, expected_result",
    [
        (
            "![image](https://github.com/demisto/content/raw/master/Packs/SplunkPy/doc_files/identify-fields-list.png)",
            "https://github.com/demisto/content/raw/master/Packs/SplunkPy/doc_files/identify-fields-list.png",
        ),
        (
            '[![Active Response in Cortex Xpanse](https://i.ytimg.com/vi/aIP1CCn9ST8/hq720.jpg)](https://www.youtube.com/watch?v=rryAQ23uuqw "Active Response in Cortex Xpanse")',
            "https://i.ytimg.com/vi/aIP1CCn9ST8/hq720.jpg",
        ),
    ],
)
def test_markdown_regex(line, expected_result):
    url = res["url"] if (res := re.search(URL_IMAGE_LINK_REGEX, line)) else ""
    assert url == expected_result
