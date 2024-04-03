from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Pack, Integration]


class IsDefaultDataSourceProvidedValidator(BaseValidator[ContentTypes]):
    error_code = "PA131"
    description = "Validate that the pack_metadata contains a default datasource if there are more than one datasource."
    rationale = "Wizards and other tools rely on the default datasource to be set."
    error_message = "Pack metadata does not contain a default datasource. Please fill in a default datasource."
    related_field = "defaultDatasource"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        datasource_count = 0
        for content_item in content_items:
            if content_item == Integration:
                fetch_incidents_command = False
                for command in content_item.commands:  # type: ignore
                    if command.name == "fetch-incidents":
                        fetch_incidents_command = True
                        break
            if MarketplaceVersions.MarketplaceV2 in content_item.marketplaces and (
                (
                    content_item.is_fetch or content_item.is_fetch_events or content_item.is_mappable or content_item.is_fetch_events_and_assets  # type: ignore
                )
                or fetch_incidents_command
            ):
                datasource_count += 1
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            if datasource_count > 1 and not content_item.default_data_source  # type: ignore
            else None
        ]
