from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.dashboard import Dashboard
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Dashboard


class IsDashboardContainForbiddenFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "DA100"
    description = "Validate that the dashboard excludes all the unnecessary fields."
    rationale = "The Dashboard should contains only the required fields."
    error_message = "the following fields need to be removed: {0}."
    related_field = ""
    is_auto_fixable = True
    fix_message = "removed the following fields {0}."
    invalid_fields: ClassVar[Dict[str, list]] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_fields)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_fields := self.contains_forbidden_fields(
                    content_item.name, content_item.data
                )
            )
        ]

    def contains_forbidden_fields(self, name, dashboard) -> List[str]:
        fields_to_exclude = [
            "system",
            "isCommon",
            "shared",
            "owner",
            "sortValues",
            "vcShouldIgnore",
            "commitMessage",
            "shouldCommit",
        ]
        invalid_fields = [
            field for field in fields_to_exclude if dashboard.get(field) is not None
        ]
        self.invalid_fields[name] = invalid_fields
        return invalid_fields

    def fix(self, content_item: ContentTypes) -> FixResult:
        for invalid_field in self.invalid_fields.get(content_item.name, []):
            content_item.data[invalid_field] = None
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.invalid_fields[content_item.name])
            ),
            content_object=content_item,
        )
