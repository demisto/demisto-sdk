import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.prepare_content.preparers.marketplace_commands_availability_preparer import (
    MarketplaceCommandsAvailabilityPreparer,
)


def test_alert_on_new_marketplace():
    """
    This test will fail whenever we are adding a new marketplace
    without ensuring the correctness of MarketplaceCommandsAvailabilityPreparer.

    When adding a new marketplace, please add a corresponding test case for each of the tests below!
    """
    assert len(list(MarketplaceVersions)) == 6


@pytest.mark.parametrize(
    "current_marketplace, expected_is_fetch_events",
    [
        (MarketplaceVersions.XSOAR, False),
        (MarketplaceVersions.XSOAR_ON_PREM, False),
        (MarketplaceVersions.XSOAR_SAAS, False),
        (MarketplaceVersions.XPANSE, False),
        (MarketplaceVersions.MarketplaceV2, True),
        (MarketplaceVersions.PLATFORM, True),
    ],
)
def test_prepare_is_fetch_events(current_marketplace, expected_is_fetch_events):
    """
    Given:
        - An integration available on different marketplaces
        - "Fetches events" is set to true

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the integration data

    Then:
        - Ensure fetch-events is available only in XSIAM and platform marketplaces
    """
    data = {"script": {"isfetchevents": True}}
    data = MarketplaceCommandsAvailabilityPreparer.prepare(data, current_marketplace)
    assert data["script"]["isfetchevents"] is expected_is_fetch_events


@pytest.mark.parametrize(
    "current_marketplace, expected_is_fetch_assets",
    [
        (MarketplaceVersions.XSOAR, False),
        (MarketplaceVersions.XSOAR_ON_PREM, False),
        (MarketplaceVersions.XSOAR_SAAS, False),
        (MarketplaceVersions.XPANSE, True),
        (MarketplaceVersions.MarketplaceV2, True),
        (MarketplaceVersions.PLATFORM, True),
    ],
)
def test_prepare_is_fetch_assets(current_marketplace, expected_is_fetch_assets):
    """
    Given:
        - An integration available on different marketplaces
        - "Fetches assets" is set to true

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the integration data

    Then:
        - Ensure fetch-assets is available only in XSIAM, platform and XPANSE marketplaces
    """
    data = {"script": {"isfetchassets": True}}
    data = MarketplaceCommandsAvailabilityPreparer.prepare(data, current_marketplace)
    assert data["script"]["isfetchassets"] is expected_is_fetch_assets


@pytest.mark.parametrize(
    "current_marketplace, expected_commands_length",
    [
        (MarketplaceVersions.XSOAR, 2),
        (MarketplaceVersions.XSOAR_ON_PREM, 2),
        (MarketplaceVersions.XSOAR_SAAS, 2),
        (MarketplaceVersions.XPANSE, 2),
        (MarketplaceVersions.MarketplaceV2, 2),
        (MarketplaceVersions.PLATFORM, 3),
    ],
)
def test_prepare_quick_actions(current_marketplace, expected_commands_length):
    """
    Given:
        - An integration available on different marketplaces
        - The integration has two commands, one of them is a quick action

    When:
        - Calling MarketplaceSuffixPreparer.prepare on the integration data

    Then:
        - Ensure only the platform keeps the quick action
    """
    data = {
        "script": {
            "commands": [
                {"name": "test"},
                {"name": "test2"},
                {"name": "test-quick-action", "quickaction": True},
            ],
        },
    }
    data = MarketplaceCommandsAvailabilityPreparer.prepare(data, current_marketplace)
    assert len(data["script"]["commands"]) == expected_commands_length
