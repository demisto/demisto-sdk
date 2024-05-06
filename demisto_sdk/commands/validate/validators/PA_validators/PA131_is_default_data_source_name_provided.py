from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsDefaultDataSourceNameProvidedValidator(BaseValidator[ContentTypes]):
    error_code = "PA131"
    description = "Validate that the pack_metadata contains a default datasource, if there are more than one datasource."
    rationale = "Wizards and other tools rely on the default datasource to be set."
    error_message = (
        "Pack metadata does not contain a 'defaultDataSourceName'. "
        "Please fill in a default datasource name from these options: {0}."
    )
    fix_message = "Set the 'defaultDataSourceName' for '{0}' pack to the '{1}' integration because it is an event collector."
    related_field = "defaultDataSourceName"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.get_valid_data_source_integrations(
                        content_item.content_items
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if MarketplaceVersions.MarketplaceV2 in content_item.marketplaces
            and (
                content_item.is_data_source(content_item.content_items)
                and not content_item.default_data_source_name
                and len(
                    content_item.get_valid_data_source_integrations(
                        content_item.content_items
                    )
                )
                > 1
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        data_sources_fetch_events = [
            integration.display_name
            for integration in content_item.content_items.integration
            if MarketplaceVersions.MarketplaceV2 in integration.marketplaces
            and not integration.deprecated
            and integration.is_fetch_events
        ]

        if len(data_sources_fetch_events) == 1:
            content_item.default_data_source_name = data_sources_fetch_events[0]
            return FixResult(
                validator=self,
                message=self.fix_message.format(
                    content_item.name, data_sources_fetch_events[0]
                ),
                content_object=content_item,
            )

        raise Exception("Cannot determine which integration to set as default.")
