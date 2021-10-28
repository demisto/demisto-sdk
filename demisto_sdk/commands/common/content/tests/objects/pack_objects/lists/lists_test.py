from demisto_sdk.commands.common.constants import LISTS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Lists
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
LIST_GOOD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LISTS_DIR / 'list-checked_integrations.json'
LIST_BAD = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LISTS_DIR / 'bad_name.json'
LIST_BAD_NORMALIZED = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / LISTS_DIR / 'list-bad_name.json'


def test_objects_factory():
    obj = path_to_pack_object(LIST_GOOD)
    assert isinstance(obj, Lists)


def test_prefix():
    obj = Lists(LIST_GOOD)
    assert obj.normalize_file_name() == LIST_GOOD.name

    obj = Lists(LIST_BAD)
    assert obj.normalize_file_name() == LIST_BAD_NORMALIZED.name
