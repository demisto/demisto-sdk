from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.generic_field import GenericField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

GENERIC_FIELD_GROUP = 4
ContentTypes = GenericField


class GenericFieldGroupValidator(BaseValidator[ContentTypes]):
    error_code = "GF100"
    description = ""
    error_message = "Group {group} is not a valid generic field group. Please set group = {generic_field_group} instead."
    fix_message = ""
    related_field = "group"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    group=group,
                    generic_field_group=GENERIC_FIELD_GROUP,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if ((group := content_item.data.get("group")) != GENERIC_FIELD_GROUP)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        pass
