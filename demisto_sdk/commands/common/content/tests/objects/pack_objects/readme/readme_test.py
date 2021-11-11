import pytest
from wcmatch.pathlib import Path

from demisto_sdk.commands.common.constants import PACKS_DIR, PLAYBOOKS_DIR
from demisto_sdk.commands.common.content.objects.pack_objects import Readme
from demisto_sdk.commands.common.content.objects.pack_objects.contributors.contributors import \
    Contributors
from demisto_sdk.commands.common.content.objects_factory import \
    path_to_pack_object
from demisto_sdk.commands.common.tools import src_root

TEST_DATA = src_root() / 'tests' / 'test_files'
TEST_CONTENT_REPO = TEST_DATA / 'content_slim'
README = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'README.md'
CONTRIBUTORS = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / 'CONTRIBUTORS.md'
PLAYBOOK_README = TEST_CONTENT_REPO / PACKS_DIR / 'Sample01' / PLAYBOOKS_DIR / 'playbook-sample_new_README.md'


@pytest.mark.parametrize(argnames="file", argvalues=[README, PLAYBOOK_README])
def test_objects_factory(file: Path):
    obj = path_to_pack_object(README)
    assert isinstance(obj, Readme)


def test_prefix():
    obj = Readme(README)
    assert obj.normalize_file_name() == README.name


def test_mention_contributors_in_readme():
    """
    Given: pack README

    When: creating artifacts, if CONTRIBUTORS file exist in the pack

    Then: Ensure credit to contributors is appended to the readme file
    """
    obj = Readme(README)
    obj.contributors = Contributors(CONTRIBUTORS)
    obj.mention_contributors_in_readme()
    with open(README, 'r') as readme_file:
        assert 'This pack was co-authored by:' in readme_file.read()
