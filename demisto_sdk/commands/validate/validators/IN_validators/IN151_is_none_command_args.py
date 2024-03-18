from __future__ import annotations

from typing import Any, ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsNoneCommandArgsValidator(BaseValidator[ContentTypes]):
    error_code = "IN151"
    description = "Validate that all commands has at least one argument"
    rationale = (
        "This prevents potential errors during execution due to missing arguments."
    )
    error_message = "The following commands arguments are None: {0}.\nIf the command has no arguments, use `arguments: []` or remove the `arguments` field."
    related_field = "script.commands"
    is_auto_fixable = True
    fix_message = "Set an empty list value to the following commands arguments: {0}."
    invalid_commands: ClassVar[Dict[str, List[str]]] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(invalid_commands)),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_commands := self.get_invalid_commands(
                    content_item.data, content_item.name
                )
            )
        ]

    def get_invalid_commands(
        self, yml_data: Dict[str, Any], integration_name: str
    ) -> List[str]:
        """iterate on the commands section in a yml and retrieve the commands with None value as an argument

        Args:
            yml_data (Dict[str, Any]): The integration yml dict.
            integration_name (str): The integration name.

        Returns:
            List[str]: The list of the names of the commands that has a None value for the argument section.
        """
        self.invalid_commands[integration_name] = [
            command.get("name")
            for command in yml_data.get("script", {}).get("commands", [])
            if "arguments" in command and command.get("arguments") is None
        ]
        return self.invalid_commands[integration_name]

    def fix(self, content_item: ContentTypes) -> FixResult:
        for command in content_item.data.get("script", {}).get("commands", []):
            if command.get("name") in self.invalid_commands[content_item.name]:
                command["arguments"] = []
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.invalid_commands[content_item.name])
            ),
            content_object=content_item,
        )
