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


class IsValidSystemFlagValidator(BaseValidator[ContentTypes]):
    error_code = "IF102"
    description = "Checks if system flag is false"
    rationale = "The 'system' key must be set to false for the platform"
    error_message = "The `system` key must be set to false"
    fix_message = "`system` field is set to false"
    related_field = "system"
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
            if (content_item.data.get("system"))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.data["system"] = False
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
