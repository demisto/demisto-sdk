from demisto_sdk.commands.common.constants import (
    PACKS_DIR,
    PLAYBOOKS_DIR,
    MarketplaceVersions,
)
from demisto_sdk.commands.common.content.objects.pack_objects import Playbook
from demisto_sdk.commands.common.content.objects_factory import path_to_pack_object
from demisto_sdk.commands.common.tools import src_root
from demisto_sdk.commands.validate.tests.test_tools import create_playbook_object

TEST_DATA = src_root() / "tests" / "test_files"
TEST_CONTENT_REPO = TEST_DATA / "content_slim"
PLAYBOOK = (
    TEST_CONTENT_REPO
    / PACKS_DIR
    / "Sample01"
    / PLAYBOOKS_DIR
    / "playbook-sample_new.yml"
)


def test_objects_factory():
    obj = path_to_pack_object(PLAYBOOK)
    assert isinstance(obj, Playbook)


def test_prefix():
    obj = Playbook(PLAYBOOK)
    assert obj.normalize_file_name() == PLAYBOOK.name


def test_playbook_summary():
    """Calling summary() on a playbook with mpv2 and incident_to_alert set to True and ensure only the name and description fields incidents appearances were modified and id didn't."""
    marketplace = MarketplaceVersions.MarketplaceV2
    playbook = create_playbook_object(
        ["id", "name", "description"],
        ["playbook-incidents", "playbook-incidents", "playbook-incidents"],
    )
    summary = playbook.summary(marketplace, True)
    assert summary["id"] == "playbook-incidents"
    assert summary["name"] == "playbook-alerts"
    assert summary["description"] == "playbook-alerts"
