from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Script


class IsBreakingContextOutputBackwardsValidator(BaseValidator[ContentTypes]):
    error_code = "BC101"
    description = "Validate that no context output keys were removed from the script's output section."
    rationale = "To ensure we don't break bc."
    error_message = "The following output keys: {0}. Has been removed, please undo."
    related_field = "outputs"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(removed_context_lines)),
                content_object=content_item,
            )
            for content_item in content_items
            if (removed_context_lines := self.get_removed_context_lines(content_item))
        ]

    def get_removed_context_lines(self, content_item: ContentTypes) -> List[str]:
        current_context: Set[str] = {
            output.contextPath for output in content_item.outputs if output.contextPath
        }
        old_context: Set[str] = set()
        if content_item.old_base_content_object:
            outputs = content_item.old_base_content_object.outputs  # type: ignore[attr-defined]
            old_context = {output.contextPath for output in outputs}
        return list(old_context - current_context)
