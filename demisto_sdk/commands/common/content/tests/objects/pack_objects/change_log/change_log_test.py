from demisto_sdk.commands.common.constants import CLASSIFIERS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import ChangeLog
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
CHNAGELOG = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / CLASSIFIERS_DIR
    / "classifier-sample_new_CHANGELOG.md"
)


def test_objects_factory():
    obj = path_to_pack_object(CHNAGELOG)
    assert isinstance(obj, ChangeLog)


def test_prefix():
    obj = ChangeLog(CHNAGELOG)
    assert obj.normalize_file_name() == CHNAGELOG.name
