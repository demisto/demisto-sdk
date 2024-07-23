from __future__ import annotations

from typing import Iterable, List

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


class IsValidRepCommandValidator(BaseValidator[ContentTypes]):
    error_code = "IN106"
    description = "Validate that the command is valid as a reputation command."
    rationale = (
        "Reputation commands must follow standards for consistency and compatibility. "
        "For more details, see https://xsoar.pan.dev/docs/integrations/generic-commands-reputation"
    )
    error_message = "The following reputation commands are invalid:\n{0}\nMake sure to fix the issue both in the yml and the code."
    related_field = "script.commands"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format("\n".join(invalid_commands)),
                content_object=content_item,
            )
            for content_item in content_items
            if (invalid_commands := self.validate_rep_commands(content_item.commands))
        ]

    def validate_rep_commands(self, commands: List[Command]) -> List[str]:
        invalid_commands = []
        for command in commands:
            if command.name in BANG_COMMAND_NAMES:
                flag_found_arg = False
                for arg in command.args:
                    if arg.name in BANG_COMMAND_ARGS_MAPPING_DICT.get(
                        command.name, {}
                    ).get("default", []):
                        # If the argument is found, validate that the argument is according to the standards.
                        flag_found_arg = True
                        if arg.default is False:
                            invalid_commands.append(
                                f"- The {command.name} command arguments are invalid, it should include the following argument with the following configuration: name should be '{arg.name}', the 'isArray' field should be True, and the default field should not be set to False."
                            )
                            break
                if not flag_found_arg and BANG_COMMAND_ARGS_MAPPING_DICT.get(
                    command.name, {}
                ).get("required", True):
                    # If the argument isn't found and is required - will fail the validation.
                    missing_arg = BANG_COMMAND_ARGS_MAPPING_DICT.get(
                        command.name, {}
                    ).get("default", [])[0]
                    invalid_commands.append(
                        f"- The {command.name} command arguments are invalid, it should include the following argument with the following configuration: name should be '{missing_arg}', the 'isArray' field should be True, and the default field should not be set to False."
                    )
        return invalid_commands
