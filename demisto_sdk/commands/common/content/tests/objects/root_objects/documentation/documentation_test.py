from demisto_sdk.commands.common.constants import DOCUMENTATION_DIR
from demisto_sdk.commands.common.content.objects.root_objects import \
    Documentation
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
DOC = TEST_CONTENT_REPO / DOCUMENTATION_DIR / 'doc-howto.json'


def test_prefix(datadir):
    obj = Documentation(DOC)
    assert obj.normalize_file_name() == DOC.name
