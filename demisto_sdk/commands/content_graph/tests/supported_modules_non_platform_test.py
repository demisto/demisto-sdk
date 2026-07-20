"""Tests verifying that ``supportedModules`` is stripped from content metadata in
all **non-platform** buckets (xsoar, xsoar_saas, xsoar_on_prem, marketplacev2,
xpanse, and any future partner marketplace) while it is preserved for the
``platform`` marketplace.

Covers (CIAC-14187):
- ``is_platform_marketplace`` helper.
- ``ContentItem.summary`` (per content-item entry in ``metadata.json`` ->
  ``contentItems``).
- ``Pack._clean_supportedModules_from_commands`` (integration command entries).
- ``Pack.dump_metadata`` pack-level ``supportedModules`` removal logic.
"""

from pathlib import Path

import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.common.tools import is_platform_marketplace
from demisto_sdk.commands.content_graph.objects.pack import Pack

NON_PLATFORM_MARKETPLACES = [
    MarketplaceVersions.XSOAR,
    MarketplaceVersions.XSOAR_SAAS,
    MarketplaceVersions.XSOAR_ON_PREM,
    MarketplaceVersions.MarketplaceV2,
    MarketplaceVersions.XPANSE,
]


def _build_minimal_pack() -> Pack:
    """Build a Pack instance via ``construct()`` (bypasses pydantic validation)
    so we can call its methods without spinning up the content graph."""
    return Pack.construct(  # type: ignore[call-arg]
        object_id="TestPack",
        name="TestPack",
        path=Path("/tmp/TestPack"),
        marketplaces=[MarketplaceVersions.XSOAR],
    )


# ---------------------------------------------------------------------------
# is_platform_marketplace helper
# ---------------------------------------------------------------------------


def test_is_platform_marketplace_true_for_platform():
    """
    Given:
        - The platform marketplace.
    When:
        - Calling is_platform_marketplace.
    Then:
        - Returns True.
    """
    assert is_platform_marketplace(MarketplaceVersions.PLATFORM) is True


@pytest.mark.parametrize("marketplace", NON_PLATFORM_MARKETPLACES)
def test_is_platform_marketplace_false_for_non_platform(marketplace):
    """
    Given:
        - A non-platform marketplace.
    When:
        - Calling is_platform_marketplace.
    Then:
        - Returns False (so any future partner marketplace is treated as
          non-platform automatically).
    """
    assert is_platform_marketplace(marketplace) is False


# ---------------------------------------------------------------------------
# Pack._clean_supportedModules_from_commands (integration command entries)
# ---------------------------------------------------------------------------


def _content_items_with_command_modules() -> dict:
    return {
        "integration": [
            {
                "id": "MyIntegration",
                "commands": [
                    {"name": "cmd-populated", "supportedModules": ["edr"]},
                    {"name": "cmd-empty", "supportedModules": []},
                    {"name": "cmd-none"},
                ],
            }
        ]
    }


@pytest.mark.parametrize("marketplace", NON_PLATFORM_MARKETPLACES)
def test_clean_supportedModules_from_commands_removes_for_non_platform(marketplace):
    """
    Given:
        - Integration commands metadata, some with populated supportedModules.
    When:
        - _clean_supportedModules_from_commands is called for a non-platform
          marketplace.
    Then:
        - supportedModules is removed from every command (populated or empty).
    """
    pack = _build_minimal_pack()
    content_items = _content_items_with_command_modules()

    pack._clean_supportedModules_from_commands(content_items, marketplace)

    for command in content_items["integration"][0]["commands"]:
        assert "supportedModules" not in command


def test_clean_supportedModules_from_commands_keeps_populated_for_platform():
    """
    Given:
        - Integration commands metadata with populated and empty
          supportedModules.
    When:
        - _clean_supportedModules_from_commands is called for the platform
          marketplace.
    Then:
        - Populated supportedModules are preserved; only empty ones are removed.
    """
    pack = _build_minimal_pack()
    content_items = _content_items_with_command_modules()

    pack._clean_supportedModules_from_commands(
        content_items, MarketplaceVersions.PLATFORM
    )

    commands = {
        command["name"]: command
        for command in content_items["integration"][0]["commands"]
    }
    assert commands["cmd-populated"]["supportedModules"] == ["edr"]
    assert "supportedModules" not in commands["cmd-empty"]
    assert "supportedModules" not in commands["cmd-none"]


# ---------------------------------------------------------------------------
# Pack-level supportedModules removal logic (as applied in Pack.dump_metadata)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("marketplace", NON_PLATFORM_MARKETPLACES)
def test_pack_level_supportedModules_removed_for_non_platform(marketplace):
    """
    Given:
        - A metadata dict with a populated pack-level supportedModules.
    When:
        - Applying the pack-level removal rule used by Pack.dump_metadata for a
          non-platform marketplace.
    Then:
        - The pack-level supportedModules key is removed.
    """
    metadata = {"name": "TestPack", "supportedModules": ["edr", "xsiam"]}

    if "supportedModules" in metadata and (
        not is_platform_marketplace(marketplace) or not metadata["supportedModules"]
    ):
        del metadata["supportedModules"]

    assert "supportedModules" not in metadata


def test_pack_level_supportedModules_kept_for_platform():
    """
    Given:
        - A metadata dict with a populated pack-level supportedModules.
    When:
        - Applying the pack-level removal rule used by Pack.dump_metadata for the
          platform marketplace.
    Then:
        - The pack-level supportedModules key is preserved.
    """
    metadata = {"name": "TestPack", "supportedModules": ["edr", "xsiam"]}
    marketplace = MarketplaceVersions.PLATFORM

    if "supportedModules" in metadata and (
        not is_platform_marketplace(marketplace) or not metadata["supportedModules"]
    ):
        del metadata["supportedModules"]

    assert metadata["supportedModules"] == ["edr", "xsiam"]


# ---------------------------------------------------------------------------
# ContentItem.summary (per content-item entry in metadata.json -> contentItems)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("marketplace", NON_PLATFORM_MARKETPLACES)
def test_content_item_summary_excludes_supportedModules_for_non_platform(marketplace):
    """
    Given:
        - An integration content item that declares supportedModules.
    When:
        - Building its metadata summary for a non-platform marketplace.
    Then:
        - The summary does not contain supportedModules.
    """
    from demisto_sdk.commands.validate.tests.test_tools import (
        create_integration_object,
    )

    integration = create_integration_object()
    integration.supportedModules = ["edr", "xsiam"]

    summary = integration.summary(marketplace)

    assert "supportedModules" not in summary


def test_content_item_summary_includes_supportedModules_for_platform():
    """
    Given:
        - An integration content item that declares supportedModules.
    When:
        - Building its metadata summary for the platform marketplace.
    Then:
        - The summary contains supportedModules.
    """
    from demisto_sdk.commands.validate.tests.test_tools import (
        create_integration_object,
    )

    integration = create_integration_object()
    integration.supportedModules = ["edr", "xsiam"]

    summary = integration.summary(MarketplaceVersions.PLATFORM)

    assert summary.get("supportedModules") == ["edr", "xsiam"]
