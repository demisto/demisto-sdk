from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.common.constants import (
    BANG_COMMAND_ARGS_MAPPING_DICT,
    BANG_COMMAND_NAMES,
)
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsRepCommandContainIsArrayArgumentValidator(BaseValidator[ContentTypes]):
    error_code = "IN144"
    description = "Validate that a reputation command has isArray field set to True for its default argument."
    rationale = (
        "Reputation commands often get multiple inputs to enrich. Without isArray=true, providing an array of inputs may impact performance."
        "For more info about reputation commands, see https://xsoar.pan.dev/docs/integrations/generic-commands-reputation"
    )
    error_message = "The following reputation commands contain default arguments without 'isArray: True':\n{0}"
    related_field = "script.commands"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        f"The command {key} is missing the isArray value on its default argument {val}."
                        for key, val in invalid_commands.items()
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_commands := self.validate_rep_commands(content_item.commands))
        ]

    def validate_rep_commands(self, commands: List[Command]) -> Dict[str, str]:
        invalid_commands = {}
        for command in commands:
            if command.name in BANG_COMMAND_NAMES:
                for arg in command.args:
                    if arg.name in BANG_COMMAND_ARGS_MAPPING_DICT.get(
                        command.name, {}
                    ).get("default", []):
                        if not arg.isArray:
                            invalid_commands[command.name] = arg.name
                        break
        return invalid_commands
