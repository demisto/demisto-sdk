from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsContainingMultipleDefaultArgsValidator(BaseValidator[ContentTypes]):
    error_code = "IN134"
    description = (
        "Validate that there're no more than 1 default argument for a command."
    )
    error_message = "The following commands have more than 1 default arg, please make sure they have at most one: {0}."
    related_field = "default"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(multiple_args_command)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                multiple_args_command := [
                    command.name
                    for command in content_item.commands
                    if len([arg.name for arg in command.args if arg.default]) >= 2
                ]
            )
        ]
