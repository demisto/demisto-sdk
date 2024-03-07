from __future__ import annotations

from typing import Iterable, List

from dateutil import parser

from demisto_sdk.commands.common.tools import check_timestamp_format
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsCreatedFieldInISOFormatValidator(BaseValidator[ContentTypes]):
    error_code = "PA115"
    description = "Validate that the pack_metadata created field is in ISO format."
    rationale = "The format is required by the platform."
    error_message = "The pack_metadata's 'created' field {} is not in ISO format."
    fix_message = "Changed the pack_metadata's 'created' field value to {}."
    related_field = "created"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.created),
                content_object=content_item,
            )
            for content_item in content_items
            if not check_timestamp_format(content_item.created)  # type: ignore[arg-type]
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.created = parser.parse(content_item.created).isoformat() + "Z"  # type: ignore[arg-type]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.created),
            content_object=content_item,
        )
