from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidDefaultDataSourceNameValidator(BaseValidator[ContentTypes]):
    error_code = "PA132"
    description = "Validate that the pack_metadata contains a valid default datasource, when provided."
    rationale = "Wizards and other tools rely on the default datasource to be set."
    error_message = (
        "Pack metadata contains an invalid 'defaultDataSourceName': {0}. "
        "Please fill in a valid datasource integration, one of these options: {1}."
    )
    related_field = "defaultDataSourceName"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.default_data_source_name,
                    content_item.get_valid_data_source_integrations(
                        content_item.content_items
                    ),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.default_data_source_name
                and content_item.default_data_source_name
                in content_item.get_valid_data_source_integrations(
                    content_item.content_items
                )
            )
        ]
