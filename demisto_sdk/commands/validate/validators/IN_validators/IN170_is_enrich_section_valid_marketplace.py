from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration

AGENTIC_ASSISTANT_SECTION = "Agentic assistant"


class IsEnrichSectionValidMarketplaceValidator(BaseValidator[ContentTypes]):
    """
    Validate that the 'Agentic assistant' section in sectionOrder is only
    used when the integration targets the 'platform' marketplace.
    """

    error_code = "IN170"
    description = (
        "Validate that the 'Agentic assistant' section is only used in "
        "integrations targeting the 'platform' marketplace."
    )
    rationale = (
        "The 'Agentic assistant' section is designed exclusively for "
        "the Platform marketplace. Integrations using this section "
        "must include 'platform' in their marketplaces list."
    )
    error_message = (
        "The 'Agentic assistant' section in sectionOrder is only valid "
        "for integrations targeting the 'platform' marketplace. Either "
        "remove the 'Agentic assistant' section or add 'platform' to "
        "the integration's marketplaces list."
    )
    related_field = "sectionorder, marketplaces"
    is_auto_fixable = False

    def _get_effective_marketplaces(
        self, content_item: ContentTypes
    ) -> List[str]:
        """
        Determines the effective list of marketplaces:
        1. Explicit list from the integration data (if exists).
        2. Marketplace list from the parent pack (if integration list is empty).
        """
        integration_marketplaces = content_item.data.get(
            "marketplaces", []
        )
        if integration_marketplaces:
            return integration_marketplaces

        if content_item.pack.marketplaces:
            return [mp.value if hasattr(mp, "value") else mp
                    for mp in content_item.pack.marketplaces]

        return []

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        invalid_items: List[ValidationResult] = []
        for content_item in content_items:
            section_order = content_item.data.get(
                "sectionorder", []
            ) or content_item.data.get("sectionOrder", [])

            if AGENTIC_ASSISTANT_SECTION in section_order:
                effective_marketplaces = (
                    self._get_effective_marketplaces(content_item)
                )
                if MarketplaceVersions.PLATFORM.value not in (
                    effective_marketplaces
                ):
                    invalid_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message,
                            content_object=content_item,
                        )
                    )
        return invalid_items
