from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.tools import compare_lists, find_command
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


# This validator checks for changes in command and argument names within the integration file.
# BC103 performs a similar validation but specifically for script arguments.
class HaveCommandsOrArgsNameChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC104"
    description = "Check if the command name or argument name has been changed."
    rationale = "If an existing command or argument has been renamed, it will break backward compatibility"
    error_message = "Possible backward compatibility break: Your updates to this file contain changes {final_message} Please undo the changes."
    related_field = "script.commands.arguments.name"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            old_content_item = content_item.old_base_content_object

            # commands name changed
            new_commands_names = [command.name for command in content_item.commands]
            old_commands_names = [command.name for command in old_content_item.commands]  # type: ignore

            commands_diff = set(old_commands_names) - set(new_commands_names)

            command_change_message = (
                "to the names of the following existing commands:"
                + ", ".join(f'"{w}"' for w in commands_diff)
                + "."
                if commands_diff
                else ""
            )

            # arguments name changed
            args_diff_per_command_summary = []
            for command in old_content_item.commands:  # type: ignore
                old_args_per_command = [argument.name for argument in command.args]
                current_command_name = command.name

                find_new_command = find_command(
                    content_item.commands, current_command_name
                )
                new_args_per_command = (
                    [argument.name for argument in find_new_command.args]
                    if find_new_command
                    else []
                )
                # Since there might be multiple arguments with the same name, we need to account for duplicates when comparing the arguments.
                if new_args_per_command:
                    diff_per_command = compare_lists(
                        old_args_per_command, new_args_per_command
                    )
                    if diff_per_command:
                        args_diff_per_command_summary.append(
                            f'In command "{current_command_name}" the following arguments have been changed: '
                            + ", ".join(f'"{w}"' for w in diff_per_command)
                        )

            args_change_message = (
                f"to the names of existing arguments: {', '.join(args_diff_per_command_summary)}."
                if args_diff_per_command_summary
                else ""
            )

            messages = [
                message
                for message in [command_change_message, args_change_message]
                if message
            ]
            final_message = (
                " In addition, you have made changes ".join(messages)
                if messages
                else None
            )

            if final_message:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(final_message=final_message),
                        content_object=content_item,
                    )
                )

        return results
