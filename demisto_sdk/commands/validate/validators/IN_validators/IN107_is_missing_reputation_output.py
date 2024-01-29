from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.common.constants import IOC_OUTPUTS_DICT
from demisto_sdk.commands.content_graph.objects.integration import (
    Command,
    Integration,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsMissingReputationOutputValidator(BaseValidator[ContentTypes]):
    error_code = "IN107"
    description = "Validate that the reputation commands include the list of required contextPaths."
    error_message = "The integration contains invalid reputation command(s):\n\t{0}"
    related_field = "script.commands"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n\t".join(
                        [
                            f"The command '{key}' is missing the following output contextPaths: {', '.join(val)}."
                            for key, val in invalid_commands.items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_commands := self.get_invalid_reputation_commands(
                    content_item.commands, content_item.name
                )
            )
        ]

    def get_invalid_reputation_commands(
        self, commands: List[Command], integration_name: str
    ) -> Dict[str, List[str]]:
        """List the reputation commands that are missing required contextPaths.

        Args:
            commands (List[Command]): The list of commands to validate.
            integration_name (str): The name of the integration being tested.

        Returns:
            Dict[str, List[str]]: The invalid commands by command_name:missing output contextPaths.
        """
        invalid_commands = {}
        for command in commands:
            if command.name in IOC_OUTPUTS_DICT:
                command_outputs = [output.contextPath for output in command.outputs]
                if missing_paths := [
                    context_path
                    for context_path in IOC_OUTPUTS_DICT[command.name]
                    if context_path not in command_outputs
                ]:
                    invalid_commands[command.name] = missing_paths
        return invalid_commands
