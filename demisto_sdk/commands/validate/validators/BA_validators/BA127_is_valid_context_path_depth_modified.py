from __future__ import annotations

from typing import Dict, Iterable, List, Set, Union

from demisto_sdk.commands.common.constants import XSOAR_SUPPORT, GitStatuses
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.BA_validators.BA127_is_valid_context_path_depth import (
    IsValidContextPathDepthValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsValidContextPathDepthModifiedValidatorModified(
    IsValidContextPathDepthValidator, BaseValidator[ContentTypes]
):
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            if content_item.support != XSOAR_SUPPORT:
                continue
            message = ""
            old_content_item = content_item.old_base_content_object
            if isinstance(content_item, Script):
                invalid_paths = self.check_for_script_invalid_paths(
                    old_content_item, content_item
                )
                if invalid_paths:
                    message = self.error_message.format(
                        "script", content_item.name, invalid_paths
                    )
            else:
                invalid_paths_dict = self.check_integration_invalid_paths(
                    old_content_item, content_item
                )
                if invalid_paths_dict:
                    message = ""
                    for command, outputs in invalid_paths_dict.items():
                        message += (
                            self.error_message.format("command", command, outputs)
                            + "\n"
                        )
            if message:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=message,
                        content_object=content_item,
                    )
                )
        return results

    def check_for_script_invalid_paths(
        self, old_content_item: BaseContent | None, content_item: BaseContent | None
    ) -> str:
        """Checking for invalid outputs.

        Args:
            old_content_item (script): The original version before change of the content item that was changed
            content_item (script)]: The content item after the change

        Returns:
             String of contextPaths that were changed
        """
        old_script_paths = self.create_outputs_set(old_content_item)
        new_script_paths = self.create_outputs_set(content_item)
        changed_paths = new_script_paths.difference(old_script_paths)
        return self.is_context_depth_larger_than_five(changed_paths)

    def check_integration_invalid_paths(
        self, old_content_item: BaseContent | None, content_item: BaseContent | None
    ) -> dict:
        """Checking for invalid outputs.

        Args:
            old_content_item (Iterable[ContentTypes]: The original version before change of the content item that was changed
            content_item (Iterable[ContentTypes]: The content item after the change

        Returns:
             Dict of [command name: contextPaths] that were changed
        """
        changed_paths_dict: Dict[str, Set[str]] = {}
        old_command_paths = self.create_command_outputs_dict(old_content_item)
        new_command_paths = self.create_command_outputs_dict(content_item)
        for command_name, command_outputs in new_command_paths.items():
            if (
                old_command_outputs := old_command_paths.get(command_name)
            ):  # if one the commands that were added is new we want to take all the context outputs for a check
                changed_paths_dict[command_name] = command_outputs.difference(
                    old_command_outputs
                )
            else:
                changed_paths_dict[command_name] = command_outputs
        return self.is_context_depth_larger_than_five_integration_commands(
            changed_paths_dict
        )
