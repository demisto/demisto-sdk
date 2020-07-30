from demisto_sdk.commands.common.content.content.objects.content_objects import ContentDescriptor
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
CONTENT_DESCRIPTOR = TEST_CONTENT_REPO / 'content-descriptor.json'


def test_changelog_prefix():
    obj = ContentDescriptor(CONTENT_DESCRIPTOR)
    assert obj._normalized_file_name() == CONTENT_DESCRIPTOR.name
