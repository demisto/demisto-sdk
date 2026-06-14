from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidProviderFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IN169"
    description = "Validate that the Integration has a provider field with a value for packs that support the platform marketplace."
    rationale = "The provider field is required to identify the service provider for integrations in packs that support the platform marketplace."
    error_message = "The Integration is missing the 'provider' field or it has an empty value. Please add a valid provider name."
    related_field = "provider"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if self._should_validate_provider(content_item)
            and (not content_item.provider or not content_item.provider.strip())
        ]

    def _should_validate_provider(self, content_item: ContentTypes) -> bool:
        """
        Check if the provider field validation should be enforced for this integration.
        Only enforce for integrations in packs that support the platform marketplace
        AND the integration itself either has no marketplace field or explicitly specifies platform.

        Args:
            content_item: The integration to check

        Returns:
            bool: True if validation should be enforced, False otherwise
        """

        # Check if the pack supports the platform marketplace
        pack_marketplaces = content_item.in_pack.marketplaces  # type: ignore
        if MarketplaceVersions.PLATFORM not in pack_marketplaces:
            return False

        # Check the integration's marketplaces field
        integration_marketplaces = content_item.marketplaces
        # Validate if:
        # 1. The integration has no marketplace field (empty list), OR
        # 2. The integration explicitly specifies platform marketplace
        return (
            not integration_marketplaces
            or MarketplaceVersions.PLATFORM in integration_marketplaces
        )
