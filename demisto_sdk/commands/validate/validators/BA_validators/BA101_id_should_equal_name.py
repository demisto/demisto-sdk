from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ContentTypes,
    FixResult,
    ValidationResult,
)


class IDNameValidator(BaseValidator[ContentTypes], ABC):
    error_code = "BA101"
    description = "Validate that the file id and name fields are identical."
    rationale = (
        "The id attribute serves as the unique identifier of files across the platform"
    )
    error_message = "The name attribute (currently {0}) should be identical to its `id` attribute ({1})"
    fix_message = "Changing name to be equal to id ({0})."
    related_field = "name"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.name,  # type: ignore[attr-defined]
                    content_item.object_id,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.object_id != content_item.name  # type: ignore[attr-defined]
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.name = content_item.object_id  # type: ignore[attr-defined]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.object_id),
            content_object=content_item,
        )
