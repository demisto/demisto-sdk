from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsDefaultDataSourceNameProvidedValidator(BaseValidator[ContentTypes]):
    error_code = "PA131"
    description = "Validate that the pack_metadata contains a default datasource, if there are more than one datasource."
    rationale = "Wizards and other tools rely on the default datasource to be set."
    error_message = "Pack metadata does not contain a 'defaultDataSourceName'. Please fill in a default datasource name."
    related_field = "defaultDataSourceName"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if MarketplaceVersions.MarketplaceV2 in content_item.marketplaces
            and (
                content_item._is_data_source
                and not content_item.default_data_source_name
            )
        ]
