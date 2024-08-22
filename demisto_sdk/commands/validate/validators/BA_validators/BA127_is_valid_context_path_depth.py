
from __future__ import annotations

from typing import Iterable, List, Union, Set

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
    description = "Validate that the level of depth of the context output path in the yml is lower or equal to 5."
    rationale = "We wish to avoid over nested context to ease on data extraction."
    error_message = "The level of depth for context output path for {0}: {1} In the yml should be less or equal to 5 check the following outputs:\n{2}"
    related_field = "contextPath"
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.ADDED]

    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.support != XSOAR_SUPPORT:
                continue
            if isinstance(content_item, Script):
                script_paths = self.create_outputs_set(content_item)
                invalid_paths_str = self.is_context_depth_larger_than_five(script_paths)
                if invalid_paths_str:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                'script', content_item.name, invalid_paths_str
                            ),
                            content_object=content_item,
                        )
                    )
            else:
                command_paths = self.create_command_outputs_dict(content_item)
                invalid_paths_dict = self.is_context_depth_larger_than_five_integration_commands(command_paths)
                if invalid_paths_dict:
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=self.error_message.format(
                                'command', invalid_paths_dict['command'], invalid_paths_dict['wrong_paths']
                            ),
                            content_object=content_item,
                        )
                )
        return results

    def is_context_depth_larger_than_five_integration_commands(self, command_paths: dict) -> dict:
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            command (Command): The command to run on

        Returns:
           List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        message = {}
        for command_name, command_outputs in command_paths.items():
            if wrong_values_string := self.is_context_depth_larger_than_five(command_outputs):
                message['command'] = command_name
                message['wrong_paths'] = wrong_values_string
        return message


    def is_context_depth_larger_than_five(self, outputs: Set[str]) -> str:
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            content_item (Iterable[ContentTypes]: The content item to run on

        Returns:
             List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        wrong_values_string = ""
        wrong_depth_values = [output for output in outputs if len(output.split('.')) > 5]
        if wrong_depth_values:
            wrong_values_string = '\n'.join(wrong_depth_values)
        return wrong_values_string


    def create_outputs_set(self, command_or_script: Command | Script) -> Set[str]:
        return set([output.contextPath for output in command_or_script.outputs])


    def create_command_outputs_dict(self, content_item) -> dict:
        command_paths = dict()
        for command in content_item.commands:
            command_paths[command.name] = self. create_outputs_set(command)
        return command_paths
