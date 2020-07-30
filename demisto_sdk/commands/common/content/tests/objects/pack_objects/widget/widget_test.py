from demisto_sdk.commands.common.constants import PACKS_DIR,WIDGETS_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import Widget
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
WIDGET = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / WIDGETS_DIR / 'widget-sample_new.json'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(WIDGET)
    assert isinstance(obj, Widget)


def test_prefix():
    obj = Widget(WIDGET)
    assert obj._normalized_file_name() == WIDGET.name
