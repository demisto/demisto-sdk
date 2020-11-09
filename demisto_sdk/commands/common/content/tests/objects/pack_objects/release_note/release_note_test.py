from demisto_sdk.commands.common.constants import PACKS_DIR, RELEASE_NOTES_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import \
    ReleaseNote
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
RELEASE_NOTE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / RELEASE_NOTES_DIR / '1_1_1.md'


def test_objects_factory():
    obj = path_to_pack_object(RELEASE_NOTE)
    assert isinstance(obj, ReleaseNote)


def test_prefix():
    obj = ReleaseNote(RELEASE_NOTE)
    assert obj.normalize_file_name() == RELEASE_NOTE.name
