from __future__ import annotations

from typing import Iterable, List, cast

from demisto_sdk.commands.common.constants import GitStatuses, RelatedFileType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = IncidentField


class IsFieldTypeChangedValidator(BaseValidator[ContentTypes]):
    error_code = "IF111"
    description = "Checks if the field type was not changed"
    rationale = "Changing type of IncidentField is not allowed by the platform"
    error_message = "Changing incident field type is not allowed"
    fix_message = "The type field has changed back"
    related_field = "type"
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.JSON]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.field_type
                != cast(ContentTypes, content_item.old_base_content_object).field_type
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.field_type = cast(
            ContentTypes, content_item.old_base_content_object
        ).field_type
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
