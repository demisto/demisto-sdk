
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsValidContextPathDepthValidator(BaseValidator[ContentTypes]):
    error_code = "BA127"
    description = "The level of depth for context output path in the yml should be less or equal to 5"
    rationale = " The depth should be less or equal to 5"
    error_message = "The level of depth for context output path for command or script: {0} In the yml should be less or equal to 5 check the following outputs:\n{1}"
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        invalid_paths: str = ""
        for content_item in content_items:
            if content_item.support_level != 'xsoar':
            old_content_item = content_item.old_base_content_object
            if isinstance(content_item, Script):
                invalid_paths = self.is_context_depth_less_or_equal_to_5_script(content_item, old_content_item)
                if invalid_paths:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                content_item.name, invalid_paths
                            ),
                            content_object=content_item,
                        )
                    )
            else:
                old_command = ""
                for command in content_item.commands:
                    if old_content_item:
                        for old_command_iterator in old_content_item.commands:
                            if command.name == old_command_iterator.name:
                                old_command = old_command_iterator
                                break
                    invalid_paths = self.is_context_depth_less_or_equal_to_5_command(command, old_command)
                    if invalid_paths:
                        results.append(
                            ValidationResult(
                                validator=self,
                                message=self.error_message.format(
                                    command.name, invalid_paths
                                ),
                                content_object=content_item,
                            )
                    )
        return results

    def is_context_depth_less_or_equal_to_5_command(self, command: Command, old_command: Command | str):
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            command (Command): The command to run on
            old_command (Command | str): The old command, to compare if the output is new or already existed
            if the command is new, then it will be empty

        Returns:
           List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        wrong_depth_values = []
        for output in command.outputs:
            if old_command:
                if output in old_command.outputs:
                    continue
            output_depth = len(output.contextPath.split('.'))
            if output_depth > 5:
                wrong_depth_values.append(output.contextPath)
        if wrong_depth_values:
            wrong_values_string = '\n'.join(wrong_depth_values)
            return wrong_values_string
        else:
            return False


    def is_context_depth_less_or_equal_to_5_script(self, content_item: Iterable[ContentTypes],
                                                   old_content_item: Iterable[ContentTypes] | str ):
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            content_item (Iterable[ContentTypes]: The content item to run on
            old_content_item (Iterable[ContentTypes] | str): The old content item, to compare if the output is new or
            already existed. If the content item is new, then it will be empty
        Returns:
             List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        wrong_depth_values = []
        for output in content_item.outputs:
            if old_content_item:
                old_ouptuts = old_content_item.outputs
                if output in old_ouptuts:
                    continue
            output_depth = len(output.contextPath.split('.'))
            if output_depth > 5:
                wrong_depth_values.append(output.contextPath)
        if wrong_depth_values:
            wrong_values_string = '\n'.join(wrong_depth_values)
            return wrong_values_string
        else:
            return False