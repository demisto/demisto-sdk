from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Trigger

# Regex: only hex characters (0-9, a-f, A-F), non-empty
VALID_TRIGGER_ID_PATTERN = re.compile(r"^[0-9a-fA-F]+$")


class IsValidTriggerIdValidator(BaseValidator[ContentTypes]):
    error_code = "TR101"
    description = "Validate that the trigger_id is a valid hex string UUID without special characters."
    rationale = (
        "The trigger_id must be a hex string containing only characters [0-9a-fA-F]. "
        "It must not contain dashes, dots, or any other special characters."
    )
    error_message = (
        "The trigger_id '{0}' is invalid. "
        "It must be a hex string containing only characters [0-9a-fA-F] "
        "with no special characters like '-' or '.'."
    )
    related_field = "trigger_id"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.object_id),
                content_object=content_item,
            )
            for content_item in content_items
            if not is_valid_trigger_id(content_item.object_id)
        ]


def is_valid_trigger_id(trigger_id: str) -> bool:
    """Check if the trigger_id is a valid hex string.

    Args:
        trigger_id: The trigger_id value to validate.

    Returns:
        bool: True if the trigger_id is a non-empty hex string, False otherwise.
    """
    if not trigger_id:
        return False
    return bool(VALID_TRIGGER_ID_PATTERN.match(trigger_id))
