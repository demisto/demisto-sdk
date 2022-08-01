from demisto_sdk.commands.common.constants import CONNECTIONS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Connection
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
CONNECTION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CONNECTIONS_DIR / 'canvas-sample_new.json'


def test_objects_factory():
    # Currently not supported auto-detect
    obj = path_to_pack_object(CONNECTION)
    assert isinstance(obj, Connection)


def test_changelog_prefix():
    obj = Connection(CONNECTION)
    assert obj.normalize_file_name() == CONNECTION.name
