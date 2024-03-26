from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import SecretIgnore
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
SECRETS_IGNORE = TEST_CONTENT_REPO / PACKS_DIR / "Sample01" / ".secrets-ignore"


def test_objects_factory():
    obj = path_to_pack_object(SECRETS_IGNORE)
    assert isinstance(obj, SecretIgnore)


def test_prefix():
    obj = SecretIgnore(SECRETS_IGNORE)
    assert obj.normalize_file_name() == SECRETS_IGNORE.name
