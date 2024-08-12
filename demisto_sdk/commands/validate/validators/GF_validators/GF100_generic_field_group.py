from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

REQUIRED_GROUP_VALUE = 4
ContentTypes = GenericField


class GenericFieldGroupValidator(BaseValidator[ContentTypes]):
    error_code = "GF100"
    rationale = "Required by the platform."
    description = f"Checks if group field is set to {REQUIRED_GROUP_VALUE}."
    error_message = f"The `group` key must be set to {REQUIRED_GROUP_VALUE}"
    fix_message = f"set the `group` field to {REQUIRED_GROUP_VALUE}."
    related_field = "group"
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
            if (content_item.group != REQUIRED_GROUP_VALUE)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.group = REQUIRED_GROUP_VALUE
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
