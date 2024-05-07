from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Dashboard


class IsDashboardContainNecessaryFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "DA101"
    description = "Validate that the dashboard includes all the necessary fields."
    rationale = "The Dashboard should contains the required 'fromDate', 'toDate', 'fromDateLicense' fields."
    error_message = "the following fields are missing and need to be added: {0}."
    related_field = ""
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(missing_fields)),
                content_object=content_item,
            )
            for content_item in content_items
            if (missing_fields := self.contains_necessary_fields(content_item.data))
        ]

    def contains_necessary_fields(self, dashboard):
        fields_to_include = ["fromDate", "toDate", "fromDateLicense"]

        return [field for field in fields_to_include if dashboard.get(field) is None]
