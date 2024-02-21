from __future__ import annotations

from typing import ClassVar, Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.tools import get_default_output_description
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class DoesCommonOutputsHaveDescriptionValidator(BaseValidator[ContentTypes]):
    error_code = "IN149"
    description = "Validate that a contextPath has a description if it belongs to a predefined list of contextPaths that should have a description."
    rationale = "Common outputs in integrations need descriptions for clarity and effective usage."
    error_message = "The following commands are missing description for the following contextPath: {0}"
    fix_message = "Added description for the following outputs: {0}"
    related_field = "output.description, output.contextPath"
    is_auto_fixable = True
    invalid_commands: ClassVar[Dict[str, Dict[str, List[str]]]] = {}
    default: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        self.default.update(get_default_output_description())
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(  # type: ignore[misc]
                        f"The command {key} is missing a description for the following contextPath: {', '.join(val)}"  # type: ignore[has-type]
                        for key, val in invalid_commands.items()
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.default
            and (
                invalid_commands := self.get_invalid_commands(
                    content_item.commands, content_item.name
                )
            )
        ]

    def get_invalid_commands(
        self, commands: List[Command], integration_name: str
    ) -> Dict[str, List[str]]:
        integration_command_missing: Dict[str, List[str]] = {}
        for command in commands:
            command_missing: List[str] = [
                output.contextPath
                for output in command.outputs
                if output.contextPath
                and output.contextPath in self.default
                and not output.description
            ]
            if command_missing:
                integration_command_missing[command.name] = command_missing
        self.invalid_commands[integration_name] = integration_command_missing
        return self.invalid_commands[integration_name]

    def format_fix_message(self, integration_name) -> str:
        error_msg = ""
        for key, values in self.invalid_commands[integration_name].items():  # type: ignore[misc]
            temp_msg = ""
            for val in values:  # type: ignore[has-type]
                temp_msg = f"{temp_msg}\n\t\tThe contextPath {val} description is now: {self.default[val]}"
            error_msg = f"{error_msg}\n\tThe command {key}: {temp_msg}"  # type: ignore[has-type]
        return error_msg

    def fix(self, content_item: ContentTypes) -> FixResult:
        for command in content_item.commands:
            if command.name in self.invalid_commands[content_item.name]:
                for output in command.outputs:
                    if (
                        output.contextPath
                        in self.invalid_commands[content_item.name][command.name]
                    ):
                        output.description = self.default[output.contextPath]
        return FixResult(
            validator=self,
            message=self.fix_message.format(self.format_fix_message(content_item.name)),
            content_object=content_item,
        )
