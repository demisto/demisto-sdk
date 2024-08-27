from __future__ import annotations

from typing import Iterable, List, Set, Union

from demisto_sdk.commands.common.constants import XSOAR_SUPPORT, GitStatuses
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

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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
                                "script", content_item.name, invalid_paths_str
                            ),
                            content_object=content_item,
                        )
                    )
            else:
                command_paths = self.create_command_outputs_dict(content_item)
                invalid_paths_dict = (
                    self.is_context_depth_larger_than_five_integration_commands(
                        command_paths
                    )
                )
                if invalid_paths_dict:
                    final_error = ""
                    for command, outputs in invalid_paths_dict.items():
                        final_error += (
                            self.error_message.format("command", command, outputs)
                            + "\n"
                        )
                    results.append(
                        ValidationResult(
                            validator=self,
                            message=final_error,
                            content_object=content_item,
                        )
                    )
        return results

    def is_context_depth_larger_than_five_integration_commands(
        self, command_paths: dict
    ) -> dict:
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            command (Command): The command to run on

        Returns:
           List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        message = {}
        for command_name, command_outputs in command_paths.items():
            if wrong_values_string := self.is_context_depth_larger_than_five(
                command_outputs
            ):
                message[command_name] = wrong_values_string
        return message

    def is_context_depth_larger_than_five(self, outputs: Set[str]) -> str:
        """Validate that all outputs entry has contextPath key for a given command.

        Args:
            content_item (Iterable[ContentTypes]: The content item to run on

        Returns:
             List of bad context paths if the contextPath depths is bigger then 5. Otherwise, return False.
        """
        wrong_depth_values = [
            output for output in outputs if len(output.split(".")) > 5
        ]
        return ", ".join(wrong_depth_values)

    def create_outputs_set(self, command_or_script: Command | Script) -> Set[str]:
        """Creates a set of context paths from command or a script.

        Args:
            command_or_script (Command | Script): The command or script to run on

        Returns:
           Set of invalid context paths
        """
        return set(
            [
                output.contextPath
                for output in command_or_script.outputs
                if output.contextPath
            ]
        )

    def create_command_outputs_dict(self, integration) -> dict:
        """Creates a dict of
         key: command name
         value: context paths from command.

        Args:
           integration: the integration to review

        Returns:
           dict of key values pairs
        """
        return {
            command.name: self.create_outputs_set(command)
            for command in integration.commands
        }
