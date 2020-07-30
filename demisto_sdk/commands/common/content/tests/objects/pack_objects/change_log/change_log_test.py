from demisto_sdk.commands.common.content.content.objects.pack_objects import ChangeLog
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files
from demisto_sdk.commands.common.constants import CLASSIFIERS_DIR, PACKS_DIR

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
CHNAGELOG = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CLASSIFIERS_DIR / 'classifier-sample_new_CHANGELOG.md'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(CHNAGELOG)
    assert isinstance(obj, ChangeLog)


def test_prefix():
    obj = ChangeLog(CHNAGELOG)
    assert obj._normalized_file_name() == CHNAGELOG.name
