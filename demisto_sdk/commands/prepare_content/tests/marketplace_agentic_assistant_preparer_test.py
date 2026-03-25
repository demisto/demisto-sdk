import pytest

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.prepare_content.preparers.marketplace_agentic_assistant_preparer import (
    MarketplaceAgenticAssistantPreparer,
)


@pytest.mark.parametrize(
    "current_marketplace, expected_config_length, expected_sectionorder",
    [
        (MarketplaceVersions.XSOAR, 1, ["Connect"]),
        (MarketplaceVersions.XSOAR_ON_PREM, 1, ["Connect"]),
        (MarketplaceVersions.XSOAR_SAAS, 1, ["Connect"]),
        (MarketplaceVersions.XPANSE, 1, ["Connect"]),
        (MarketplaceVersions.MarketplaceV2, 1, ["Connect"]),
        (MarketplaceVersions.PLATFORM, 2, ["Connect", "Agentic assistant"]),
    ],
)
def test_prepare_agentic_assistant(
    current_marketplace, expected_config_length, expected_sectionorder
):
    """
    Given:
        An integration data dict with a configuration parameter in the "Agentic assistant" section and a sectionorder containing "Agentic assistant".
    When:
        Calling MarketplaceAgenticAssistantPreparer.prepare on the integration data.
    Then:
        Ensure "Agentic assistant" params and sectionorder entries are removed for unsupported marketplaces and kept only for platform.
    """
    data = {
        "configuration": [
            {"name": "url", "section": "Connect"},
            {"name": "agent_param", "section": "Agentic assistant"},
        ],
        "sectionorder": ["Connect", "Agentic assistant"],
    }
    data = MarketplaceAgenticAssistantPreparer.prepare(data, current_marketplace)
    assert len(data["configuration"]) == expected_config_length
    assert data["sectionorder"] == expected_sectionorder
