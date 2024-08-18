
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses,XSOAR_SUPPORT
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
    error_message = "The level of depth for context output path for {0}: {1} In the yml should be less or equal to 5 check the following outputs:\n{2}"
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.support_level != XSOAR_SUPPORT:
                continue
            if isinstance(content_item, Script):
                script_paths = self.create_script_outputs_list(content_item)
                invalid_paths = self.is_context_depth_less_or_equal_to_5_script(script_paths)
                if invalid_paths:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                'script', content_item.name, invalid_paths
                            ),
                            content_object=content_item,
                        )
                    )
            else:
                command_paths = self.create_command_outputs_dict(content_item)
                invalid_paths = self.is_context_depth_less_or_equal_to_5_command(command_paths)
                if invalid_paths:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                'command', invalid_paths['command'], invalid_paths['wrong_paths']
                            ),
                            content_object=content_item,
                        )
                )
        return results

    def is_context_depth_less_or_equal_to_5_command(self, command_paths: dict):
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            command (Command): The command to run on

        Returns:
           List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        wrong_depth_values = []
        message = {}
        for command in command_paths.keys():
            for path in command_paths[command]:
                output_depth = len(path.split('.'))
                if output_depth > 5:
                    wrong_depth_values.append(path)
            if wrong_depth_values:
                wrong_values_string = '\n'.join(wrong_depth_values)
                message['command'] = command
                message['wrong_paths'] = wrong_values_string
                return message
            else:
                return False


    def is_context_depth_less_or_equal_to_5_script(self, script_paths: list ):
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            content_item (Iterable[ContentTypes]: The content item to run on

        Returns:
             List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        wrong_depth_values = []
        message = {}
        for output in script_paths:
            output_depth = len(output.split('.'))
            if output_depth > 5:
                wrong_depth_values.append(output)
        if wrong_depth_values:
            wrong_values_string = '\n'.join(wrong_depth_values)
            return wrong_values_string
        else:
            return False


    def create_script_outputs_list(self, content_item) -> list:
        script_paths = list()
        for output in content_item.outputs:
            script_paths.append(output.contextPath)
        return script_paths


    def create_command_outputs_dict(self, content_item) -> dict:
        command_paths = dict()
        for command in content_item.commands:
            command_paths[command.name] = []
            for output in command.outputs:
                command_paths[command.name].append(output.contextPath)
        return command_paths
