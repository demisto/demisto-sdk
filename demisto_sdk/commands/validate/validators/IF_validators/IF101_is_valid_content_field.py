from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[CaseField, IncidentField]


class IsValidContentFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IF101"
    description = "Checks if the incident field is marked as content."
    rationale = "Required by the platform."
    error_message = "The `content` key must be set to true."
    fix_message = "`content` field is set to true."
    related_field = "content"
    is_auto_fixable = True

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
            if (not content_item.content)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.content = True
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
