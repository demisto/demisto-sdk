from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects import XSIAMDashboard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[XSIAMDashboard]


class XSIAMDashboardStandardizedFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "XD101"
    description = "Validate that XSIAM Dashboards use standardized 'id' field instead of 'global_id' in dashboards_data."
    rationale = "New content items should use standardized field names 'id' and 'name' for consistency across all content types."
    error_message = "XSIAM Dashboards must use 'id' field instead of 'global_id' in dashboards_data. Please update your dashboard to use the standardized field name."
    related_field = "global_id"
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

        # Check dashboards_data for non-standard fields
        dashboards_data = data.get("dashboards_data", [])

        for dashboard in dashboards_data:
            has_global_id = "global_id" in dashboard
            has_standard_id = "id" in dashboard

            # Invalid if it has the old field but not the new standard field
            if has_global_id and not has_standard_id:
                return True

        return False
