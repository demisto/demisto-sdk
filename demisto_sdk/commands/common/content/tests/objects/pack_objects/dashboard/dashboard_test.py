from demisto_sdk.commands.common.content.content.objects.pack_objects import Dashboard
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.constants import DASHBOARDS_DIR, PACKS_DIR
from demisto_sdk.commands.common.tools import path_test_files


TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
DASHBOARD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / DASHBOARDS_DIR / 'dashboard-sample_new.json'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(DASHBOARD)
    assert isinstance(obj, Dashboard)


def test_prefix():
    obj = Dashboard(DASHBOARD)
    assert obj.normalized_file_name() == DASHBOARD.name
