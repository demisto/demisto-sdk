from demisto_sdk.commands.common.constants import REPORTS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import Report
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
REPORT = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / REPORTS_DIR / 'report-sample_new.json'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(REPORT)
    assert isinstance(obj, Report)


def test_prefix():
    obj = Report(REPORT)
    assert obj._normalized_file_name() == REPORT.name
