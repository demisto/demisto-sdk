from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.xsiam_dashboard_image.xsiam_dashboard_image import (
    XSIAMDashboardImage,
)
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
XSIAM_DASHBOARD_IMAGE_FILE = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / "XSIAMDashboards"
    / "MyDashboard_image.png"
)


def test_prefix():
    obj = XSIAMDashboardImage(XSIAM_DASHBOARD_IMAGE_FILE)
    assert obj.normalize_file_name() == f"{XSIAM_DASHBOARD_IMAGE_FILE.name}"
