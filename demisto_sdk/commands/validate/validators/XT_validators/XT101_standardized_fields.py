from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects import XDRCTemplate
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[XDRCTemplate]


class XDRCTemplateStandardizedFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "XT101"
    description = "Validate that XDRCTemplates use standardized 'id' field instead of 'content_global_id'."
    rationale = "New content items should use standardized field names 'id' and 'name' for consistency across all content types."
    error_message = "XDRCTemplates must use 'id' field instead of 'content_global_id'. Please update your template to use the standardized field name."
    related_field = "content_global_id"
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
            if self.has_non_standard_fields(content_item)
        ]

    def has_non_standard_fields(self, content_item: ContentTypes) -> bool:
        """Check if the content item uses non-standard field names."""
        data = content_item.data

        # Check for non-standard fields
        has_content_global_id = "content_global_id" in data
        has_standard_id = "id" in data

        # Invalid if it has the old field but not the new standard field
        return has_content_global_id and not has_standard_id
