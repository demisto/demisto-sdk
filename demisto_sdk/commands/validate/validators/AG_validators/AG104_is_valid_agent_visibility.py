from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects import AgentixAgent
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAgent

VALID_VISIBILITY_VALUES = ["public", "private"]


class IsValidAgentVisibilityValidator(BaseValidator[ContentTypes]):
    error_code = "AG104"
    description = "Validate that Agentix Agent visibility field has a valid value."
    rationale = "The visibility field must be either 'public' or 'private' to ensure proper access control."
    error_message = (
        "The following Agentix agent '{0}' has an invalid visibility value: '{1}'.\n"
        "Valid visibility values are: {2}."
    )
    related_field = "visibility"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name,
                    content_item.visibility,
                    ", ".join(VALID_VISIBILITY_VALUES),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.visibility not in VALID_VISIBILITY_VALUES
        ]
