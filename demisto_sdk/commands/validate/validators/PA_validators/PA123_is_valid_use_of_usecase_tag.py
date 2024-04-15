from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import USE_CASE_TAG
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsValidUseOfUsecaseTagValidator(BaseValidator[ContentTypes]):
    error_code = "PA123"
    description = "Validate that the pack has at least one of PB, incidents Types or Layouts if the tags section contains the 'Use Case' tag."
    rationale = "Correct categorization helps users find packs that suit their needs."
    error_message = "Tags section contain the 'Use Case' tag, without having any PB, incidents Types or Layouts as part of the pack."
    fix_message = "Removed the 'Use Case' tag from the tags list."
    related_field = "tags"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.tags
            and USE_CASE_TAG in content_item.tags
            and not any(
                [
                    content_item.content_items.playbook,
                    content_item.content_items.incident_type,
                    content_item.content_items.layout,
                ]
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        tags = content_item.tags
        tags.remove(USE_CASE_TAG)
        content_item.tags = tags
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
