from demisto_sdk.commands.common.constants import PACKS_DIR, PLAYBOOKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Playbook
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
PLAYBOOK = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PLAYBOOKS_DIR / 'playbook-sample_new.yml'


def test_objects_factory():
    obj = path_to_pack_object(PLAYBOOK)
    assert isinstance(obj, Playbook)


def test_prefix():
    obj = Playbook(PLAYBOOK)
    assert obj.normalize_file_name() == PLAYBOOK.name
