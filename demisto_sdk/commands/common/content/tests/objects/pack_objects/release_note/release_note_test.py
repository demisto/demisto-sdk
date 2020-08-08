from demisto_sdk.commands.common.constants import PACKS_DIR, RELEASE_NOTES_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import ReleaseNote
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
RELEASE_NOTE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / RELEASE_NOTES_DIR / '1_1_1.md'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(RELEASE_NOTE)
    assert isinstance(obj, ReleaseNote)


def test_prefix():
    obj = ReleaseNote(RELEASE_NOTE)
    assert obj.normalized_file_name() == RELEASE_NOTE.name
