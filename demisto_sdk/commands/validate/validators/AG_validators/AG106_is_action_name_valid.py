from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


class IsActionNameValidValidator(BaseValidator[ContentTypes]):
    error_code = "AG106"
    description = (
        "AgentixAction name value may contain only letters (uppercase or lowercase), digits, "
        "or underscores. Spaces and special characters are not allowed."
    )
    rationale = "Action names must be user-friendly and conform to standards."
    error_message = (
        "The following AgentixAction name value is invalid: {0}.\n"
        "AgentixAction name value may contain only letters (uppercase or lowercase), digits, or underscores. "
        "Spaces and special characters are not allowed."
    )

    related_field = "name"
    is_auto_fixable = False

    AGENTIX_ACTION_NAME_PATTERN = re.compile(r"^[a-z0-9_]+$", re.IGNORECASE)

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        validation_results = []
        for content_item in content_items:
            action_name = getattr(content_item, "name", None)
            if not action_name or not self.AGENTIX_ACTION_NAME_PATTERN.match(
                action_name
            ):
                validation_results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            action_name,
                        ),
                        content_object=content_item,
                    )
                )
        return validation_results
