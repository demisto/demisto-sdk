from __future__ import annotations

from typing import ClassVar, Iterable, List

from demisto_sdk.commands.common.constants import (
    BANG_COMMAND_ARGS_MAPPING_DICT,
    BANG_COMMAND_NAMES,
)
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidRepCommandValidator(BaseValidator[ContentTypes]):
    error_code = "IN106"
    description = "Validate that the command is valid as a reputation command."
    error_message = "The following reputation commands are invalid:\n{0}"
    fix_message = "Fixed the following reputation commands to match the standards: {0}"
    related_field = "script"
    is_auto_fixable = True
    invalid_rep_commands: ClassVar[dict] = {}

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "\n".join(
                        [
                            f"- The {key} command display name should be '{val['display']}', the 'defaultvalue' field should be 'False', the 'required' field should be 'False', and the 'required' field should be 8."
                            for key, val in self.invalid_rep_commands[
                                content_item.name
                            ].items()
                        ]
                    )
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if not all(
                [
                    self.validate_rep_command(command, content_item.name)
                    for command in content_item.commands
                    if command.name in BANG_COMMAND_NAMES
                ]
            )
        ]

    def validate_rep_command(self, rep_command: Command, integration_name):
        flag_found_arg = False
        for arg in rep_command.args:
            arg_name = arg.get("name")
            if arg_name in BANG_COMMAND_ARGS_MAPPING_DICT.get(arg_name, {}).get("default", False):
                flag_found_arg = True
                if arg.get("default", False) in ("false", False) or arg.get(
                    "isArray", False
                ) in ("false", False):
                    self.invalid_rep_commands[
                        integration_name
                    ] = self.invalid_rep_commands.get(integration_name, {})
                    self.invalid_rep_commands[integration_name][rep_command.name] = {
                        "arguments": {
                            "name": arg_name,
                            "default": True,
                            "isArray": True,
                        }
                    }
                    return False
            if not flag_found_arg and BANG_COMMAND_ARGS_MAPPING_DICT.get(
                "required", True
            ):
                self.invalid_rep_commands[
                    integration_name
                ] = self.invalid_rep_commands.get(integration_name, {})
                self.invalid_rep_commands[integration_name][rep_command.name] = {
                    "arguments": {
                        "name": arg_name,
                        "default": True,
                        "isArray": True,
                        "required": True,
                    }
                }
                return False
        return True

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        for key, val in self.invalid_rep_commands[content_item.name]:
            for command in content_item.commands:
                if command.name == key:
                    if "required" in val:
                        command.args.append(val)
                    else:
                        for arg in command.args:
                            if arg.get("name", "") == val.get("name", ""):
                                arg.update(val)
                                break
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(list(self.invalid_rep_commands[content_item.name].keys()))
            ),
            content_object=content_item,
        )
