from demisto_sdk.commands.common.constants import PLAYBOOKS_DIR, PACKS_DIR
from demisto_sdk.commands.common.content.content.objects.pack_objects import Playbook
from demisto_sdk.commands.common.content.content.objects_factory import ContentObjectFacotry
from demisto_sdk.commands.common.tools import path_test_files

TEST_DATA = path_test_files()
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PLAYBOOK = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PLAYBOOKS_DIR / 'playbook-sample_new.yml'


def test_objects_factory():
    obj = ContentObjectFacotry.from_path(PLAYBOOK)
    assert isinstance(obj, Playbook)


def test_prefix():
    obj = Playbook(PLAYBOOK)
    assert obj._normalized_file_name() == PLAYBOOK.name
