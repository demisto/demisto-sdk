import pytest
from demisto_sdk.commands.common.content.content.objects.pack_objects import Connection
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.constants import CONNECTIONS_DIR, PACKS_DIR
from demisto_sdk.commands.common.tools import path_test_files


TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
CONNECTION = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / CONNECTIONS_DIR / 'canvas-sample_new.json'


def test_objects_factory():
    # Currently not supported auto-detect
    obj = ContentObjectFacotry.from_path(CONNECTION)
    assert isinstance(obj, Connection)


def test_changelog_prefix():
    obj = Connection(CONNECTION)
    assert obj._normalized_file_name() == CONNECTION.name
