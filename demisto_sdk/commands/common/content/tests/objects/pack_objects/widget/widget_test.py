from demisto_sdk.commands.common.constants import PACKS_DIR, WIDGETS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Widget
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
WIDGET = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / WIDGETS_DIR / 'widget-sample_new.json'


def test_objects_factory():
    obj = path_to_pack_object(WIDGET)
    assert isinstance(obj, Widget)


def test_prefix():
    obj = Widget(WIDGET)
    assert obj.normalize_file_name() == WIDGET.name
