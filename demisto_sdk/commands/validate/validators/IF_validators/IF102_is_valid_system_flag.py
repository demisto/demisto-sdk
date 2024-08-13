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


class IsValidSystemFlagValidator(BaseValidator[ContentTypes]):
    error_code = "IF102"
    description = "Checks if system flag is false."
    rationale = "Required by the platform."
    error_message = "The `system` key must be set to false."
    fix_message = "`system` field is set to false."
    related_field = "system"
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
            if (content_item.system)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.system = False
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
