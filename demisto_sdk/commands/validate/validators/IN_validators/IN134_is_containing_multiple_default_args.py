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
    rationale = (
        "Multiple default arguments could lead to unexpected behavior. "
        "For more info about command arguments, see https://xsoar.pan.dev/docs/integrations/yaml-file#command-arguments"
    )
    rationale = "A command in an integration should have at most one default argument to prevent ambiguity during execution. Having multiple default arguments could lead to unexpected behavior, as it's unclear which argument should be used if no value is provided by the user. for more info see https://xsoar.pan.dev/docs/integrations/yaml-file#command-arguments"
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
