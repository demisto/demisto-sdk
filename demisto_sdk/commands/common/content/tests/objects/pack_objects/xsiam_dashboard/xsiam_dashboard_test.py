from demisto_sdk.commands.common.constants import (PACKS_DIR,
                                                   XSIAM_DASHBOARDS_DIR)
from demisto_sdk.commands.common.content.objects.pack_objects import \
    XSIAMDashboard
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
XSIAM_DASHBOARD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / XSIAM_DASHBOARDS_DIR / 'xsiamdashboard-sample.json'
XSIAM_DASHBOARD_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / XSIAM_DASHBOARDS_DIR / 'sample_bad.json'
XSIAM_DASHBOARD_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / XSIAM_DASHBOARDS_DIR / 'xsiamdashboard-sample_bad.json'


def test_objects_factory():
    obj = path_to_pack_object(XSIAM_DASHBOARD)
    assert isinstance(obj, XSIAMDashboard)


def test_prefix():
    obj = XSIAMDashboard(XSIAM_DASHBOARD)
    assert obj.normalize_file_name() == XSIAM_DASHBOARD.name

    obj = XSIAMDashboard(XSIAM_DASHBOARD_BAD)
    assert obj.normalize_file_name() == XSIAM_DASHBOARD_BAD_NORMALIZED.name
