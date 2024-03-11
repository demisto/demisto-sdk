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

INCIDENT_FIELD_GROUP = 0


class IsValidGroupFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IF104"
    description = "Checks if group number is valid"
    rationale = "IncidentField must be group `0` for mapping of the platform"
    error_message = "Group {group} is not a group field"
    fix_message = f"`group` field is set to {INCIDENT_FIELD_GROUP}"
    related_field = "group"
    is_auto_fixable = True
    related_file_type = [RelatedFileType.JSON]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(group=content_item.data["group"]),
                content_object=content_item,
            )
            for content_item in content_items
            if (content_item.data["group"] != INCIDENT_FIELD_GROUP)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.data["group"] = INCIDENT_FIELD_GROUP
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
