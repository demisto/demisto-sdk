from __future__ import annotations

from collections import Counter
from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class HaveCommandsOrArgsNameChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC104"
    description = "Check if the command name or argument name has been changed."
    rationale = "If an existing command or argument has been renamed, it will break backward compatibility"
    error_message = "Possible backward compatibility break: Your updates to this file contain changes to the names of the following existing {type_and_list} Please undo the changes."
    related_field = "name"  # TODO - what is the field name?
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.YML]

    def compare_names(self, old_names, new_names):
        return list((Counter(old_names) - Counter(new_names)).elements())

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            old_content_item = content_item.old_base_content_object

            # commands name changed or deleted
            new_commands_names = [command.name for command in content_item.commands]
            old_commands_names = [command.name for command in old_content_item.commands]  # type: ignore

            commands_diff = self.compare_names(old_commands_names, new_commands_names)
            if commands_diff:
                type_and_list = f"commands: {', '.join(commands_diff)}."
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(type_and_list=type_and_list),
                        content_object=content_item,
                    )
                )

            # arguments name changed or deleted
            new_args_names = [
                arg.name for command in content_item.commands for arg in command.args
            ]
            old_args_names = [
                arg.name
                for command in old_content_item.commands  # type: ignore
                for arg in command.args
            ]

            args_diff = self.compare_names(old_args_names, new_args_names)
            if args_diff:
                type_and_list = f"arguments: {', '.join(args_diff)}."
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(type_and_list=type_and_list),
                        content_object=content_item,
                    )
                )

        return results
