from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsEmptyCommandArgsValidator(BaseValidator[ContentTypes]):
    error_code = "IN151"
    description = "Validate that all commands has at least one argument"
    error_message = "The following commands doesn't include any arguments: {0}.\nPlease make sure to include at least one argument."
    related_field = "script.commands"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_commands)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_commands := [
                    command.name
                    for command in content_item.commands
                    if not command.args
                ]
            )
        ]
