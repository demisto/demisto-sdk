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


class IsSiemIntegrationValidMarketplaceValidator(BaseValidator[ContentTypes]):
    error_code = "IN161"
    description = "Validate that the marketplacev2 tag appear in the marketplaces list of a siem integration."
    rationale = (
        "SIEM integrations must have the 'marketplacev2' tag for visibility in marketplacev2, enhancing usability. "
        "Refer to https://xsoar.pan.dev/docs/integrations/event-collectors#required-keys."
    )
    error_message = "The marketplaces field of this XSIAM integration is incorrect.\nThis field should have only the 'marketplacev2' value."
    fix_message = (
        "Added the 'marketplacev2' entry to the integration's marketplaces list."
    )
    related_field = "isfetchevents, marketplaces"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.display_name),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_fetch_events
            and MarketplaceVersions.MarketplaceV2 not in content_item.marketplaces
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.marketplaces.append(MarketplaceVersions.MarketplaceV2)
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.display_name),
            content_object=content_item,
        )
