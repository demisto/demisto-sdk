from demisto_sdk.commands.common.content.objects.root_objects import ContentDescriptor
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
CONTENT_DESCRIPTOR = TEST_CONTENT_REPO / "content-descriptor.json"


def test_changelog_prefix():
    obj = ContentDescriptor(CONTENT_DESCRIPTOR)
    assert obj.normalize_file_name() == CONTENT_DESCRIPTOR.name
