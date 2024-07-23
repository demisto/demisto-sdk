from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsValidDefaultDataSourceNameValidator(BaseValidator[ContentTypes]):
    error_code = "PA132"
    description = "Validate that the pack_metadata contains a valid default datasource, when provided."
    rationale = "Wizards and other tools rely on the default datasource to be set."
    error_message = (
        "Pack metadata contains an invalid 'defaultDataSource': {0}. "
        "Please fill in a valid datasource integration, one of these options: {1}."
    )
    fix_message = (
        "Updated the 'defaultDataSource' for the '{0}' pack to use the '{1}' "
        "integration ID instead of the display name that was previously used."
    )
    related_field = "defaultDataSource"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.default_data_source_id,
                    content_item.get_valid_data_source_integrations(
                        content_item.content_items, content_item.support
                    ),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.default_data_source_id
                and content_item.default_data_source_id
                not in content_item.get_valid_data_source_integrations(
                    content_item.content_items, content_item.support
                )
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        # The fix applies when the defaultDataSource value is the display name instead of the id of the selected integration
        data_sources: List[Dict[str, str]] = (
            content_item.get_valid_data_source_integrations(  # type: ignore[assignment]
                content_item.content_items, content_item.support, include_name=True
            )
        )

        default_data_source = [
            data_source
            for data_source in data_sources
            if data_source.get("name") == content_item.default_data_source_id
        ]

        if default_data_source:
            content_item.default_data_source_id = default_data_source[0].get("id")
            return FixResult(
                validator=self,
                message=self.fix_message.format(
                    content_item.name, default_data_source[0].get("id")
                ),
                content_object=content_item,
            )

        raise Exception(
            "Unable to determine which integration should be set as default."
        )
