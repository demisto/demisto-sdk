from demisto_sdk.commands.common.constants import PACKS_DIR, XSIAM_REPORTS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import \
    XSIAMReport
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
XSIAM_REPORT = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / XSIAM_REPORTS_DIR / 'xsiamreport-sample.json'
XSIAM_REPORT_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / XSIAM_REPORTS_DIR / 'sample_bad.json'
XSIAM_REPORT_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / XSIAM_REPORTS_DIR / 'xsiamreport-sample_bad.json'


def test_objects_factory():
    obj = path_to_pack_object(XSIAM_REPORT)
    assert isinstance(obj, XSIAMReport)


def test_prefix():
    obj = XSIAMReport(XSIAM_REPORT)
    assert obj.normalize_file_name() == XSIAM_REPORT.name

    obj = XSIAMReport(XSIAM_REPORT_BAD)
    assert obj.normalize_file_name() == XSIAM_REPORT_BAD_NORMALIZED.name
