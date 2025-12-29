from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


REQUIRED_MARKETPLACE = MarketplaceVersions.PLATFORM.value


class IsMcpIntegrationValidMarketplaceValidator(BaseValidator[ContentTypes]):
    """
    Validate that an integration marked with ismcp: true has
    MarketplaceVersions.PLATFORM as its only marketplace, checking both
    the integration file and the parent pack (if the integration field is empty).
    """

    error_code = "IN168"
    description = "Validate that an integration with ismcp: true has only PLATFORM in its marketplaces list."
    rationale = (
        "Integrations marked with 'ismcp: true' are designed exclusively for the "
        "Platform platform and must only be available on 'platform'."
    )
    error_message = (
        "The marketplaces field of the integration is incorrect for an ismcp: true integration.\n"
        "This field should have only the 'platform' value."
    )
    fix_message = "Set the integration's marketplaces list to contain only 'platform'."
    related_field = "ismcp, marketplaces"
    is_auto_fixable = True

    def _get_effective_marketplaces(self, content_item: ContentTypes) -> List[str]:
        """
        Determines the effective list of marketplaces:
        1. Explicit list from the integration data (if exists).
        2. Marketplace list from the parent pack (if integration list is empty).
        """
        # 1. Check marketplaces explicitly set in the integration's file (data)
        integration_marketplaces = content_item.data.get("marketplaces", [])

        if integration_marketplaces:
            return integration_marketplaces

        # 2. If the integration list is empty, check the parent pack's marketplaces
        if content_item.pack.marketplaces:
            return content_item.pack.marketplaces

        # If neither is set, return an empty list (which will fail the validation check below)
        return []

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        invalid_items: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.is_mcp:
                effective_marketplaces = self._get_effective_marketplaces(content_item)

                # The effective marketplaces list must be exactly ['platform']
                is_valid = (
                    len(effective_marketplaces) == 1
                    and effective_marketplaces[0] == REQUIRED_MARKETPLACE
                )

                if not is_valid:
                    invalid_items.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                content_item.display_name
                            ),
                            content_object=content_item,
                        )
                    )
        return invalid_items

    def fix(self, content_item: ContentTypes) -> FixResult:
        # For the fix, we directly set the 'marketplaces' field in the integration data,
        # ensuring it overrides any pack settings.
        content_item.data["marketplaces"] = [REQUIRED_MARKETPLACE]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.display_name),
            content_object=content_item,
        )
