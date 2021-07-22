from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import \
    AuthorImage
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
AUTHOR_IMAGE_FILE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'valid_author_image.png'


def test_objects_factory():
    obj = path_to_pack_object(AUTHOR_IMAGE_FILE)
    assert isinstance(obj, AuthorImage)


def test_prefix():
    obj = AuthorImage(AUTHOR_IMAGE_FILE)
    assert obj.normalize_file_name() == AUTHOR_IMAGE_FILE.name
