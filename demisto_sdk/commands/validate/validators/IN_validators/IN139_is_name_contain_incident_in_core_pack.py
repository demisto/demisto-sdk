from __future__ import annotations

from typing import ClassVar, Iterable, List

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
    error_message = "The following commands contain the word 'incident' in their name, please remove: {0}"
    fix_message = "Fixed and modified the following commands: {0}"
    related_field = "name"
    is_auto_fixable = True
    invalid_commands: ClassVar[dict[str, dict]] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        core_packs_list = get_core_pack_list()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(self.create_results_list(invalid_commands))
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.pack_name in core_packs_list
            and bool(
                invalid_commands := self.is_containing_invalid_commands(
                    content_item.commands, content_item.name
                )
            )
        ]

    def create_results_list(self, invalid_commands) -> List[str]:
        results = []
        for key, val in invalid_commands:
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
    ) -> dict:
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


#     def fix(self, content_item: ContentTypes) -> FixResult:
#         fixed_commands = []
#         for command in content_item.commands:
#             current_command = self.invalid_commands.get(command.name, {})
#             if current_command:
#                 fixed_command = {}
#                 if current_command["incident_in_name"]:
#                     command.name = command.name.replace("incident", "")
#                     fixed_command["name"] = command.name
#                 if (current_args := current_command["args"]):
#                     fixed_command["args"] = []
#                     for arg in command.args:
#                         if arg.name in current_args:
#                             arg.name = arg.name.replace("incident", "")
#                             fixed_command["args"].append(arg.name)
#                 fixed_commands.append(fixed_command)

#         return FixResult(
#             validator=self,
#             message=self.fix_message.format([[f"The command {old_key}: {f"changed command name to {new_val.get('name', "")} {', and' if new_val.get('args') else ''}" if new_val.get('name', "") else ''} {f'changed the following arguments: {', '.join([f"{old_arg_name} -> {new_arg_name}" for old_arg_name, new_arg_name in zip(old_val_value['args'], new_val['args'])])}' if old_val_value['args'] else ''}" for old_key, old_val_value in old_val.items()] for old_val, new_val in zip(self.invalid_commands[content_item.name], fixed_commands)]),
#             content_object=content_item,
#         )
