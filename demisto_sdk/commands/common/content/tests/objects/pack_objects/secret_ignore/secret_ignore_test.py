from demisto_sdk.commands.common.constants import PACKS_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import SecretIgnore
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
SECRETS_IGNORE = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / ".secrets-ignore"


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(SECRETS_IGNORE)
    assert isinstance(obj, SecretIgnore)


def test_prefix():
    obj = SecretIgnore(SECRETS_IGNORE)
    assert obj._normalized_file_name() == SECRETS_IGNORE.name
