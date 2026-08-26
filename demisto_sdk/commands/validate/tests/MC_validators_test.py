from pathlib import Path
from typing import List, Optional

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.common import (
    TIGHTLY_COUPLED_TYPES,
    ContentType,
)
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.content_graph.objects.pack_content_items import (
    PackContentItems,
)
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.test_playbook import TestPlaybook
from demisto_sdk.commands.validate.tests.test_tools import (
    create_pack_object,
)
from demisto_sdk.commands.validate.validators.MC_validators.MC101_managed_pack_has_deployment_json import (
    DEPLOYMENT_JSON_FILENAME,
    ManagedPackHasDeploymentJsonValidator,
)
from demisto_sdk.commands.validate.validators.MC_validators.MC102_no_loose_item_added_to_tightly_coupled_pack import (
    NoLooseItemAddedToTightlyCoupledPackValidator,
)


@pytest.mark.parametrize(
    "managed, has_deployment_json, expected_result_len",
    [
        # Valid cases - should pass
        (False, False, 0),  # Non-managed pack, no deployment.json required
        (False, True, 0),  # Non-managed pack, deployment.json present (irrelevant)
        (True, True, 0),  # Managed pack with deployment.json present
        # Invalid cases - should fail
        (True, False, 1),  # Managed pack missing deployment.json
    ],
)
def test_ManagedPackHasDeploymentJsonValidator(
    managed, has_deployment_json, expected_result_len
):
    """
    Given:
        - Various combinations of packs with different managed values
          and presence/absence of deployment.json.

    When:
        - Running ManagedPackHasDeploymentJsonValidator.obtain_invalid_content_items.

    Then:
        - Managed packs (managed: true) must have a deployment.json file.
        - Non-managed packs are always valid regardless of deployment.json presence.
    """
    pack = create_pack_object(
        paths=["managed"],
        values=[managed],
    )

    if has_deployment_json:
        (pack.path / DEPLOYMENT_JSON_FILENAME).write_text("{}")

    invalid_content_items = (
        ManagedPackHasDeploymentJsonValidator().obtain_invalid_content_items([pack])
    )

    assert len(invalid_content_items) == expected_result_len


def test_ManagedPackHasDeploymentJsonValidator_error_message():
    """
    Given:
        - A managed pack (managed: true) without a deployment.json file.

    When:
        - Running ManagedPackHasDeploymentJsonValidator.obtain_invalid_content_items.

    Then:
        - The validation result message should mention the missing deployment.json.
    """
    pack = create_pack_object(
        paths=["managed"],
        values=[True],
    )

    invalid_content_items = (
        ManagedPackHasDeploymentJsonValidator().obtain_invalid_content_items([pack])
    )

    assert len(invalid_content_items) == 1
    assert "deployment.json" in invalid_content_items[0].message
    assert "managed" in invalid_content_items[0].message


# ---------------------------------------------------------------------------
# MC102 – NoLooseItemAddedToTightlyCoupledPackValidator
# ---------------------------------------------------------------------------

PACK_ID = "TestPack"


def _make_integration(object_id: str, deprecated: bool = False) -> Integration:
    return Integration(
        id=object_id,
        content_type=ContentType.INTEGRATION,
        node_id=f"{ContentType.INTEGRATION}:{object_id}",
        path=Path(f"{object_id}.yml"),
        fromversion="6.0.0",
        toversion="99.99.99",
        display_name=object_id,
        name=object_id,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=deprecated,
        type="python3",
        docker_image="demisto/python3:3.10.11.54799",
        category="Utilities",
        commands=[],
    )


def _make_playbook(object_id: str) -> Playbook:
    return Playbook(
        id=object_id,
        content_type=ContentType.PLAYBOOK,
        node_id=f"{ContentType.PLAYBOOK}:{object_id}",
        path=Path(f"{object_id}.yml"),
        fromversion="6.0.0",
        toversion="99.99.99",
        display_name=object_id,
        name=object_id,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        is_test=False,
    )


def _make_test_playbook(object_id: str) -> TestPlaybook:
    return TestPlaybook(
        id=object_id,
        content_type=ContentType.TEST_PLAYBOOK,
        node_id=f"{ContentType.TEST_PLAYBOOK}:{object_id}",
        path=Path(f"{object_id}.yml"),
        fromversion="6.0.0",
        toversion="99.99.99",
        display_name=object_id,
        name=object_id,
        marketplaces=[MarketplaceVersions.XSOAR],
        deprecated=False,
        is_test=True,
    )


# Maps the content types used by these tests to their `PackContentItems` field.
CONTENT_TYPE_TO_PACK_FIELD = {
    ContentType.INTEGRATION: "integration",
    ContentType.PLAYBOOK: "playbook",
    ContentType.TEST_PLAYBOOK: "test_playbook",
}


def _make_pack(
    content_items: List[ContentItem],
    support: str = "xsoar",
    coupling_overrides: Optional[dict] = None,
) -> Pack:
    """Build a real ``Pack`` holding the given real content items.

    ``support`` is exposed because only xsoar-supported packs are ever split into a
    managed twin, which is a precondition of the rule under test.
    """
    pack_content_items = PackContentItems()
    for item in content_items:
        getattr(
            pack_content_items, CONTENT_TYPE_TO_PACK_FIELD[item.content_type]
        ).append(item)

    pack = Pack(
        object_id=PACK_ID,
        content_type=ContentType.PACK,
        node_id=f"Pack:{PACK_ID}",
        path=Path(PACK_ID),
        name=PACK_ID,
        display_name=PACK_ID,
        marketplaces=[MarketplaceVersions.XSOAR],
        current_version="1.0.0",
        description="A pack used to exercise MC102.",
        created="2024-01-01T00:00:00Z",
        support=support,
        author="Cortex XSOAR",
        certification="certified",
        hidden=False,
        deprecated=False,
        tags=[],
        categories=[],
        useCases=[],
        keywords=[],
        contentItems=pack_content_items,
        coupling_overrides=coupling_overrides,
    )
    for item in content_items:
        item.pack = pack
    return pack


def test_MC102_loosely_coupled_item_added_to_fully_tightly_coupled_pack_fails():
    """
    Given:
        - An existing pack whose only content item is a tightly coupled integration.
        - A newly added loosely coupled playbook.

    When:
        - Running NoLooseItemAddedToTightlyCoupledPackValidator.obtain_invalid_content_items
          on the added playbook.

    Then:
        - The playbook is reported, since a fully tightly coupled pack must stay that way.
    """
    assert (
        ContentType.INTEGRATION in TIGHTLY_COUPLED_TYPES
        and ContentType.PLAYBOOK not in TIGHTLY_COUPLED_TYPES
    ), "test premise: an integration is tightly coupled and a playbook is loosely coupled"
    added_playbook = _make_playbook("MyPlaybook")
    _make_pack([_make_integration("MyIntegration"), added_playbook])

    results = (
        NoLooseItemAddedToTightlyCoupledPackValidator().obtain_invalid_content_items(
            [added_playbook]
        )
    )

    assert len(results) == 1
    assert "MyPlaybook" in results[0].message
    assert PACK_ID in results[0].message


def test_MC102_tightly_coupled_item_added_to_fully_tightly_coupled_pack_passes():
    """
    Given:
        - An existing pack whose only content item is a tightly coupled integration.
        - A newly added tightly coupled integration.

    When:
        - Running the validator on the added integration.

    Then:
        - Nothing is reported: the pack stays fully tightly coupled.
    """
    added_integration = _make_integration("NewIntegration")
    _make_pack([_make_integration("MyIntegration"), added_integration])

    assert not NoLooseItemAddedToTightlyCoupledPackValidator().obtain_invalid_content_items(
        [added_integration]
    )


def test_MC102_pack_already_holding_a_loosely_coupled_item_passes():
    """
    Given:
        - An existing pack holding both a tightly coupled integration and a loosely
          coupled playbook.
        - A newly added loosely coupled playbook.

    When:
        - Running the validator on the added playbook.

    Then:
        - Nothing is reported: the pack was already mixed, so nothing is being lost.
    """
    added_playbook = _make_playbook("NewPlaybook")
    _make_pack(
        [
            _make_integration("MyIntegration"),
            _make_playbook("ExistingPlaybook"),
            added_playbook,
        ]
    )

    assert not NoLooseItemAddedToTightlyCoupledPackValidator().obtain_invalid_content_items(
        [added_playbook]
    )


def test_MC102_brand_new_pack_passes():
    """
    Given:
        - A pack whose every content item is part of this very change (a brand-new pack),
          holding a tightly coupled integration and a loosely coupled playbook.

    When:
        - Running the validator on both added items.

    Then:
        - Nothing is reported: the rule only protects packs that already existed.
    """
    added_integration = _make_integration("MyIntegration")
    added_playbook = _make_playbook("MyPlaybook")
    _make_pack([added_integration, added_playbook])

    assert not NoLooseItemAddedToTightlyCoupledPackValidator().obtain_invalid_content_items(
        [added_integration, added_playbook]
    )


def test_MC102_non_xsoar_supported_pack_passes():
    """
    Given:
        - A partner-supported pack holding only a tightly coupled integration.
        - A newly added loosely coupled playbook.

    When:
        - Running the validator on the added playbook.

    Then:
        - Nothing is reported: a non-xsoar pack never splits into a managed twin,
          so it has no full-tightly-coupled property to preserve.
    """
    added_playbook = _make_playbook("MyPlaybook")
    _make_pack(
        [_make_integration("MyIntegration"), added_playbook],
        support="partner",
    )

    assert not NoLooseItemAddedToTightlyCoupledPackValidator().obtain_invalid_content_items(
        [added_playbook]
    )


def test_MC102_coupling_override_to_tightly_coupled_passes():
    """
    Given:
        - An existing pack holding only a tightly coupled integration.
        - A newly added playbook that the pack's coupling_overrides declares tightly coupled.

    When:
        - Running the validator on the added playbook.

    Then:
        - Nothing is reported: the override, not the content type, decides.
    """
    added_playbook = _make_playbook("MyPlaybook")
    _make_pack(
        [_make_integration("MyIntegration"), added_playbook],
        coupling_overrides={"MyPlaybook": "tightly_coupled"},
    )

    assert not NoLooseItemAddedToTightlyCoupledPackValidator().obtain_invalid_content_items(
        [added_playbook]
    )


def test_MC102_added_test_playbook_is_ignored():
    """
    Given:
        - An existing pack holding only a tightly coupled integration.
        - A newly added test playbook.

    When:
        - Running the validator on the added test playbook.

    Then:
        - Nothing is reported: test items never travel to Managed Content.
    """
    added_test_playbook = _make_test_playbook("MyTestPlaybook")
    _make_pack([_make_integration("MyIntegration"), added_test_playbook])

    assert not NoLooseItemAddedToTightlyCoupledPackValidator().obtain_invalid_content_items(
        [added_test_playbook]
    )
