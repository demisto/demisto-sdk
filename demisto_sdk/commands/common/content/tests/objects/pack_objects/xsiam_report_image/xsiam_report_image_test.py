from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects.xsiam_report_image.xsiam_report_image import (
    XSIAMReportImage,
)
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
XSIAM_REPORT_IMAGE_FILE = (
    TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / "XSIAMReports" / "MyReport_image.png"
)


def test_prefix():
    obj = XSIAMReportImage(XSIAM_REPORT_IMAGE_FILE)
    assert obj.normalize_file_name() == f"{XSIAM_REPORT_IMAGE_FILE.name}"
