from demisto_sdk.commands.common.constants import PACKS_DIR, REPORTS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Report
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
REPORT = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / REPORTS_DIR / 'report-sample_new.json'


def test_objects_factory():
    obj = path_to_pack_object(REPORT)
    assert isinstance(obj, Report)


def test_prefix():
    obj = Report(REPORT)
    assert obj.normalize_file_name() == REPORT.name
