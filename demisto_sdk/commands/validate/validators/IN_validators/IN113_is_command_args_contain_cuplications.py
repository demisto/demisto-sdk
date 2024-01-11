from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsCommandArgsContainCuplicationsValidator(BaseValidator[ContentTypes]):
    error_code = "IN113"
    description = "Validate that there're no duplicated params for the integration."
    error_message = "The following commands contain duplicated arguments:\n{0}\nPlease make sure to remove the duplications."
    related_field = "script.commands"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    [
                        ".\n".join(
                            f"command {key}, contains multiple appearances of the following arguments {', '.join(val)}"
                        )
                        for key, val in duplicated_args_by_command.items()
                    ]
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                duplicated_args_by_command := self.is_containing_dups(
                    content_item.commands
                )
            )
        ]

    def is_containing_dups(self, commands: List[Command]) -> Dict[str, set]:
        duplicated_args_by_command = {}
        for command in commands:
            appeared_set = set()
            for command in commands:
                if duplicated_args := set(
                    arg.get("name", "")
                    for arg in command.args
                    if (
                        arg.get("name", "") in appeared_set
                        or appeared_set.add(arg.get("name", ""))
                    )
                ):
                    duplicated_args_by_command[command.name] = duplicated_args
        return duplicated_args_by_command
