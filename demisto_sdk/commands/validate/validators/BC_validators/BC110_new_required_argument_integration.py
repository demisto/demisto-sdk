from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.tools import find_command
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


# This validation is similar to BC111, but specifically for integrations.
class NewRequiredArgumentIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "BC110"
    description = (
        "Validate that no new *required* argument are added to an existing command."
    )
    rationale = "Adding a new argument to an existing command and defining it as *required* or changing an non-required argument to be required will break backward compatibility."
    error_message = "Possible backward compatibility break: You have added the following new *required* arguments: {custom_message} Please undo the changes."
    related_field = "script.commands.arguments"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        custom_message = ""
        for content_item in content_items:
            old_content_item = content_item.old_base_content_object

            for new_command in content_item.commands:  # type: ignore
                current_command_name = new_command.name

                old_corresponding_command = find_command(
                    old_content_item.commands,  # type: ignore[union-attr]
                    current_command_name,
                )
                # If the command is new, there is no need to check for its arguments
                if old_corresponding_command:
                    for arg in new_command.args:
                        if arg.required and not arg.defaultvalue:
                            old_corresponding_arg = next(
                                (
                                    old_arg
                                    for old_arg in old_corresponding_command.args
                                    if old_arg.name == arg.name
                                ),
                                None,
                            )

                            if (
                                not old_corresponding_arg
                            ) or not old_corresponding_arg.required:
                                custom_message += f"in command '{current_command_name}' you have added a new required argument:'{arg.name}'. "
            if custom_message:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            custom_message=custom_message
                        ),
                        content_object=content_item,
                    )
                )

        return results
