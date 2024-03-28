from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.tools import compare_lists, find_command
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class HaveCommandsOrArgsNameChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC104"
    description = "Check if the command name or argument name has been changed."
    rationale = "If an existing command or argument has been renamed, it will break backward compatibility"
    error_message = "Possible backward compatibility break: Your updates to this file: {file_path} contain changes {unique_message} Please undo the changes."
    related_field = "name"  # TODO - what is the field name?
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            old_content_item = content_item.old_base_content_object

            # commands name changed
            new_commands_names = [command.name for command in content_item.commands]
            old_commands_names = [command.name for command in old_content_item.commands]  # type: ignore

            commands_diff = compare_lists(
                sub_list=old_commands_names, main_list=new_commands_names
            )
            if commands_diff:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            file_path=content_item.path,
                            unique_message=f"to the names of the following existing commands: {', '.join(commands_diff)}.",
                        ),
                        content_object=content_item,
                    )
                )

            # arguments name changed
            args_diff_per_command_summary = []
            for command in content_item.old_base_content_object.commands:  # type: ignore
                new_args_per_command = []
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

                if new_args_per_command:
                    diff_per_command = compare_lists(
                        sub_list=old_args_per_command, main_list=new_args_per_command
                    )
                    if diff_per_command:
                        args_diff_per_command_summary.append(
                            f"In command '{current_command_name}' the following arguments have been changed: {', '.join(diff_per_command)}."
                        )
            if args_diff_per_command_summary:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            file_path=content_item.path,
                            unique_message=f"to the names of existing arguments: {' '.join(args_diff_per_command_summary)}",
                        ),
                        content_object=content_item,
                    )
                )

        return results


# TODO is it ok to return 2 validation results, one for args and one for commands?
# TODO do i need to add the file path?
# TODO do I need to add a new validation for 103 as i did for 104?
