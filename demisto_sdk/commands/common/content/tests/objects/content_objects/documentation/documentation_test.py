from demisto_sdk.commands.common.content.content.objects.content_objects import Documentation
from demisto_sdk.commands.common.tools import path_test_files
from demisto_sdk.commands.common.constants import DOCUMENTATION_DIR

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
DOC = TEST_CONTENT_REPO / DOCUMENTATION_DIR / 'doc-howto.json'


def test_prefix(datadir):
    obj = Documentation(DOC)
    assert obj._normalized_file_name() == DOC.name
