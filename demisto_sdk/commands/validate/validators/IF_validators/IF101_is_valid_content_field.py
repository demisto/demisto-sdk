from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = IncidentField


class IsValidContentFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IF101"
    description = "Validates that the field is marked as content."
    error_message = "The content key must be set to True."
    fix_message = "Content field is set to true."
    related_field = "content"
    is_auto_fixable = True
    related_file_type = [RelatedFileType.JSON]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (not content_item.data.get("content"))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.data["content"] = True
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
