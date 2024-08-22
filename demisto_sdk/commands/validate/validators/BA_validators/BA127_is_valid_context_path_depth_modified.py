
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses,XSOAR_SUPPORT
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)
from demisto_sdk.commands.validate.validators.BA_validators.BA127_is_valid_context_path_depth import (
    IsValidContextPathDepthValidator,
)
ContentTypes = Union[Integration, Script]


class IsValidContextPathDepthModifiedValidatorModified(IsValidContextPathDepthValidator, BaseValidator[ContentTypes]):
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        invalid_paths: str = ""
        for content_item in content_items:
            if content_item.support != XSOAR_SUPPORT:
                continue
            old_content_item = content_item.old_base_content_object
            if isinstance(content_item, Script):
                old_script_paths = self.create_outputs_set(old_content_item)
                new_script_paths = self.create_outputs_set(content_item)
                changed_paths = set(new_script_paths).difference(old_script_paths)
                invalid_paths = self.is_context_depth_larger_than_five(changed_paths)
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
                for command in content_item.commands:
                    changed_paths = {}
                    old_command_paths = self.create_command_outputs_dict(old_content_item)
                    command_paths = self.create_command_outputs_dict(content_item)
                    for k in command_paths.keys():
                        if k in old_command_paths:
                            changed_paths[k] = set(command_paths[k]).difference(old_command_paths[k])
                    invalid_paths = self.is_context_depth_larger_than_five_integration_commands(changed_paths)
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
