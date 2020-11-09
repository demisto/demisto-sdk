from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import \
    PackMetaData
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PACK_METADATA = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'pack_metadata.json'


def test_objects_factory():
    obj = path_to_pack_object(PACK_METADATA)
    assert isinstance(obj, PackMetaData)


def test_prefix():
    obj = PackMetaData(PACK_METADATA)
    assert obj.normalize_file_name() == PACK_METADATA.name
