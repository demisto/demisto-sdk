from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.constants import IOC_OUTPUTS_DICT
from demisto_sdk.commands.content_graph.objects.integration import (
    Command,
    Integration,
    Output,
)
from demisto_sdk.commands.validate.tools import find_command
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsMissingReputationOutputValidator(BaseValidator[ContentTypes]):
    error_code = "IN107"
    description = (
        "Validate that the reputation commands include the list of required params."
    )
    error_message = "The validation contain invalid reputation commands: {0}"
    fix_message = "The following contextPaths have been added to the following commands:{0}\nPlease make sure to fill in the description."
    related_field = "script.commands"
    is_auto_fixable = True
    invalid_commands: ClassVar[Dict[str, Dict[str, List[str]]]]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n\t".join(
                        [
                            f"The command {key} is missing the following output contextPaths: {', '.join(val)}."
                            for key, val in invalid_commands.items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if bool(
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
        self.invalid_commands[integration_name] = invalid_commands
        return invalid_commands

    def fix(self, content_item: ContentTypes) -> FixResult:
        for invalid_command, missing_context_paths in self.invalid_commands[
            content_item.name
        ].items():
            if current_command := find_command(content_item.commands, invalid_command):
                for missing_context_path in missing_context_paths:
                    current_command.outputs.append(
                        Output(description="", contextPath=missing_context_path)
                    )
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                "\n\t".join(
                    [
                        f"Added the following output contextPaths: {', '.join(val)} to the command {key}."
                        for key, val in self.invalid_commands[content_item.name].items()
                    ]
                )
            ),
            content_object=content_item,
        )
