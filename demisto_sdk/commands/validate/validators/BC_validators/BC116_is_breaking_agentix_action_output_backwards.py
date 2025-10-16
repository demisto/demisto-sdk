from __future__ import annotations

from typing import Iterable, List, Set

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


class IsBreakingAgentixActionOutputBackwardsValidator(BaseValidator[ContentTypes]):
    error_code = "BC116"
    description = "Validate that no context output keys were removed from the Agentix action's output section."
    rationale = "To ensure we don't break backward compatibility."
    error_message = "The following output keys: {0} have been removed, please undo."
    related_field = "outputs"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(removed_outputs)),
                content_object=content_item,
            )
            for content_item in content_items
            if (removed_outputs := self.get_removed_outputs(content_item))
        ]

    def get_removed_outputs(self, content_item: ContentTypes) -> List[str]:
        current_outputs: Set[str] = set()
        if content_item.outputs:
            current_outputs = {
                output.content_item_output_name for output in content_item.outputs
            }

        old_outputs: Set[str] = set()
        if (
            content_item.old_base_content_object
            and content_item.old_base_content_object.outputs  # type: ignore[attr-defined]
        ):
            old_outputs = {
                output.content_item_output_name
                for output in content_item.old_base_content_object.outputs  # type: ignore[attr-defined]
            }

        return list(old_outputs - current_outputs)
