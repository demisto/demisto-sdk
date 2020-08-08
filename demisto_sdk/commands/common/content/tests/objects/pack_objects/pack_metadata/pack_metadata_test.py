from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import PackMetaData
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PACK_METADATA = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'pack_metadata.json'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(PACK_METADATA)
    assert isinstance(obj, PackMetaData)


def test_prefix():
    obj = PackMetaData(PACK_METADATA)
    assert obj.normalized_file_name() == PACK_METADATA.name
