from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import Readme
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
README = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'README.md'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(README)
    assert isinstance(obj, Readme)


def test_prefix():
    obj = Readme(README)
    assert obj.normalized_file_name() == README.name
