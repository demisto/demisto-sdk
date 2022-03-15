from demisto_sdk.commands.common.constants import PACKS_DIR, TRIGGER_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Trigger
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
TRIGGER = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / TRIGGER_DIR / 'trigger-sample.json'
TRIGGER_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / TRIGGER_DIR / 'sample_bad.json'
TRIGGER_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / TRIGGER_DIR / 'trigger-sample_bad.json'


def test_objects_factory():
    obj = path_to_pack_object(TRIGGER)
    assert isinstance(obj, Trigger)


def test_prefix():
    obj = Trigger(TRIGGER)
    assert obj.normalize_file_name() == TRIGGER.name

    obj = Trigger(TRIGGER_BAD)
    assert obj.normalize_file_name() == TRIGGER_BAD_NORMALIZED.name
