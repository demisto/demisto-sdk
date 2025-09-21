from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects import XSIAMReport
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[XSIAMReport]


class XSIAMReportStandardizedFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "XR101"
    description = "Validate that XSIAM Reports use standardized 'id' and 'name' fields instead of 'global_id' and 'report_name' in templates_data."
    rationale = "New content items should use standardized field names 'id' and 'name' for consistency across all content types."
    error_message = "XSIAM Reports must use 'id' and 'name' fields instead of 'global_id' and 'report_name' in templates_data. Please update your report to use the standardized field names."
    related_field = "global_id, report_name"
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

        # Check templates_data for non-standard fields
        templates_data = data.get("templates_data", [])

        for template in templates_data:
            has_global_id = "global_id" in template
            has_report_name = "report_name" in template
            has_standard_id = "id" in template
            has_standard_name = "name" in template

            # Invalid if it has old fields but not the corresponding new standard fields
            if (has_global_id and not has_standard_id) or (has_report_name and not has_standard_name):
                return True

        return False
