from __future__ import annotations

from typing import Any, ClassVar, Dict, Iterable, List

from demisto_sdk.commands.common.tools import get_core_pack_list
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsNameContainIncidentInCorePackValidator(BaseValidator[ContentTypes]):
    error_code = "IN139"
    description = "Validate that there's no 'incident' in any of the commands names or arguments names for core packs integrations."
    rationale = "This helps maintain the flexibility of the platform."
    error_message = "The following commands contain the word 'incident' in one or more of their fields, please remove:\n{0}"
    related_field = "name"
    invalid_commands: ClassVar[Dict[str, dict]] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        core_packs_list = get_core_pack_list()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(self.create_invalid_commands_errors(invalid_commands))
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.pack_name in core_packs_list
            and (
                invalid_commands := self.is_containing_invalid_commands(
                    content_item.commands, content_item.name
                )
            )
        ]

    def create_invalid_commands_errors(
        self, invalid_commands: Dict[str, Dict[str, Any]]
    ) -> List[str]:
        results = []
        for key, val in invalid_commands.items():
            current_str = f"The command {key} contains the word 'incident' in "
            if val["incident_in_name"]:
                current_str += "its name"
                if val["args"]:
                    current_str += " and in "
                else:
                    current_str += "."
            if val["args"]:
                current_str += f"the following arguments: {', '.join(val['args'])}."
            results.append(current_str)
        return results

    def is_containing_invalid_commands(
        self, commands: List[Command], integration_name: str
    ) -> Dict[str, Dict[str, Any]]:
        self.invalid_commands[integration_name] = {}
        for command in commands:
            current_command = {}
            current_command["incident_in_name"] = "incident" in command.name
            current_command["args"] = [  # type: ignore[assignment]
                arg.name for arg in command.args if "incident" in arg.name
            ]
            if current_command["incident_in_name"] or current_command["args"]:
                self.invalid_commands[integration_name][command.name] = current_command
        return self.invalid_commands[integration_name]
