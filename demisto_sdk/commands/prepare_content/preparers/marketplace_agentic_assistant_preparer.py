from demisto_sdk.commands.common.constants import (
    MARKETPLACES_NO_AGENTIC_ASSISTANT,
    MarketplaceVersions,
)
from demisto_sdk.commands.content_graph.strict_objects.integration import (
    SectionOrderValues,
)


class MarketplaceAgenticAssistantPreparer:
    @staticmethod
    def prepare(
        data: dict,
        current_marketplace: MarketplaceVersions,
    ) -> dict:
        """
        Removes Agentic assistant configuration parameters and sectionorder entries
        for marketplaces that do not support Agentic assistant.

        Args:
            data: integration data dict
            current_marketplace: the marketplace to prepare for

        Returns: A (possibly) modified integration data
        """
        if current_marketplace in MARKETPLACES_NO_AGENTIC_ASSISTANT:
            agentic_section = SectionOrderValues.AGENTIC_ASSISTANT.value
            data["configuration"] = [
                param
                for param in data.get("configuration", [])
                if param.get("section") != agentic_section
            ]
            if "sectionorder" in data:
                data["sectionorder"] = [
                    section
                    for section in data["sectionorder"]
                    if section != agentic_section
                ]
        return data
