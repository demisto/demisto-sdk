from demisto_sdk.commands.common.content.content.objects.pack_objects import IndicatorField
from demisto_sdk.commands.common.constants import INDICATOR_FIELDS_DIR, PACKS_DIR
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
INDICATOR_FIELD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / INDICATOR_FIELDS_DIR / 'incidentfield-sample.json'


def test_prefix():
    obj = IndicatorField(INDICATOR_FIELD)
    assert obj.normalized_file_name() == f"incidentfield-indicatorfield-sample.json"
