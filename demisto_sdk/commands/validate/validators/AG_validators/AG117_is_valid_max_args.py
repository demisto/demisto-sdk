from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects import AgentixAction
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction

MAX_ACTION_ARGS = 10


class IsValidMaxArgsValidator(BaseValidator[ContentTypes]):
    error_code = "AG117"
    description = (
        f"Enforce a maximum of {MAX_ACTION_ARGS} arguments per Agentix Action."
    )
    rationale = (
        "Too many arguments make an action hard for an agent to call correctly "
        "and increase the chance of wrong parameter mapping."
    )
    error_message = (
        "The Agentix action '{0}' has {1} arguments, which exceeds the maximum "
        f"allowed of {MAX_ACTION_ARGS}. Please reduce the number of arguments."
    )
    related_field = "args"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name,
                    len(content_item.args or []),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if len(content_item.args or []) > MAX_ACTION_ARGS
        ]
