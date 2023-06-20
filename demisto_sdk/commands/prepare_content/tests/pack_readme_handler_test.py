import os
from pathlib import Path
from demisto_sdk.commands.prepare_content.pack_readme_handler import collect_images_from_readme_and_replace_with_storage_path
from demisto_sdk.commands.common.constants import README_IMAGES, MarketplaceVersions, MarketplaceVersionToMarketplaceName
import pytest


expected_urls_ret = {
    "original_read_me_url": "https://raw.githubusercontent.com/crestdatasystems/content/"
    "4f707f8922d7ef1fe234a194dcc6fa73f96a4a87/Packs/Lansweeper/doc_files/"
    "Retrieve_Asset_Details_-_Lansweeper.png",
    "new_gcs_image_path": Path(os.path.dirname(os.path.abspath(__file__)),
        "test_data",'readme_images_test_data', README_IMAGES, 'Retrieve_Asset_Details_-_Lansweeper.png'),
    "image_name": "Retrieve_Asset_Details_-_Lansweeper.png",
    "pack_name": "readme_images_test_data"
}


@pytest.mark.parametrize(
    "marketplace, expected_res", [(MarketplaceVersions.XSOAR, expected_urls_ret)]
)
def test_collect_images_from_readme_and_replace_with_storage_path(
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

    ret = collect_images_from_readme_and_replace_with_storage_path(
        pack_readme_path=path_readme_to_replace_url, marketplace=marketplace
    )

    assert ret == [expected_res]

    replaced = Path(path_readme_to_replace_url).read_text()
    expected = Path(
        os.path.join(readme_images_test_folder_path, "README_after_replace.md")
    ).read_text()
    assert replaced == expected
