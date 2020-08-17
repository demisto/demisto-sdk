from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Readme
from demisto_sdk.commands.common.content.objects_factory import \
    ContentObjectFactory
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
README = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'README.md'


def test_objects_factory():
    obj = ContentObjectFactory.from_path(README)
    assert isinstance(obj, Readme)


def test_prefix():
    obj = Readme(README)
    assert obj.normalize_file_name() == README.name
