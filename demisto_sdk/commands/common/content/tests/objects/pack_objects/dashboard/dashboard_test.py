from demisto_sdk.commands.common.constants import DASHBOARDS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Dashboard
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
DASHBOARD = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / DASHBOARDS_DIR
    / "dashboard-sample_new.json"
)


def test_objects_factory():
    obj = path_to_pack_object(DASHBOARD)
    assert isinstance(obj, Dashboard)


def test_prefix():
    obj = Dashboard(DASHBOARD)
    assert obj.normalize_file_name() == DASHBOARD.name
