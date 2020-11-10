from demisto_sdk.commands.common.constants import DOC_FILES_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import DocFile
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
DOC_FILE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / DOC_FILES_DIR / 'sample_packs.png'


def test_objects_factory():
    obj = path_to_pack_object(DOC_FILE)
    assert isinstance(obj, DocFile)


def test_prefix():
    obj = DocFile(DOC_FILE)
    assert obj.normalize_file_name() == DOC_FILE.name
