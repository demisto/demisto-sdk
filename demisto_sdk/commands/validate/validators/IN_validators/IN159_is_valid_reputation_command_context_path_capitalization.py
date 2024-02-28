from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    BANG_COMMAND_NAMES,
    MANDATORY_REPUTATION_CONTEXT_NAMES,
    XSOAR_CONTEXT_AND_OUTPUTS_URL,
)
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidReputationCommandContextPathCapitalizationValidator(
    BaseValidator[ContentTypes]
):
    error_code = "IN159"
    description = "Validate that the capitalization of reputation command specific keys is correct."
    rationale = (
        "This ensures consistency and effective data passage between playbook tasks. "
        "For more about the standard context output for reputation commands see: https://xsoar.pan.dev/docs/integrations/context-standards-mandatory"
    )
    error_message = "The following reputation commands contains invalid contextPath capitalization: {0}"
    related_field = "script.commands"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format("\n".join(invalid_commands)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_commands := self.validate_rep_commands_outputs_capitalization(
                    content_item.commands
                )
            )
        ]

    def validate_rep_commands_outputs_capitalization(
        self, commands: List[Command]
    ) -> List[str]:
        invalid_commands = []
        for command in commands:
            if command.name in BANG_COMMAND_NAMES:
                invalid_outputs_per_command = []
                for output in command.outputs:
                    for reputation_name in MANDATORY_REPUTATION_CONTEXT_NAMES:
                        if (
                            output.contextPath
                            and output.contextPath.lower().startswith(
                                f"{reputation_name.lower()}."
                            )
                            and reputation_name not in output.contextPath
                        ):
                            invalid_outputs_per_command.append(
                                f"\t{output.contextPath} for reputation: {reputation_name}."
                            )
                if invalid_outputs_per_command:
                    invalid_outputs = "\n".join(invalid_outputs_per_command)
                    invalid_commands.append(
                        f"The command '{command.name}' returns the following invalid reputation outputs:\n{invalid_outputs}\nThe capitalization is incorrect, for further information refer to {XSOAR_CONTEXT_AND_OUTPUTS_URL}"
                    )
        return invalid_commands
