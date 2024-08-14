from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Command, Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


def diff_outputs_context_path(
    new_command: Command, old_command: Command
) -> Set[Optional[str]]:
    """
    This method returns the context path diff between two commands objects.
    """
    old_command_outputs_set = {output.contextPath for output in old_command.outputs}
    new_command_outputs_set = {output.contextPath for output in new_command.outputs}
    return old_command_outputs_set.difference(new_command_outputs_set)


def is_context_path_changed(integration: Integration) -> dict[str, Set[Optional[str]]]:
    """
    This method returns the diff between the integrations versions per command.
    """
    result = defaultdict(set)
    old_integration = integration.old_base_content_object
    old_command_outputs = {
        # Since we're sure old_integration has 'commands' attribute, we ignore it (down casting does not solve it)
        command.name: command
        for command in old_integration.commands  # type:ignore[union-attr]
    }
    new_command_outputs = {command.name: command for command in integration.commands}

    for command in sorted(old_command_outputs):
        if command in new_command_outputs:
            if diff := diff_outputs_context_path(
                new_command_outputs[command], old_command_outputs[command]
            ):
                result[command] = diff

        # in case the command has been removed and does not exist in the new commands
        else:
            result[command] = {
                f"Command {command} has been removed from the integration. This is a breaking change, and is not allowed."
            }

    return result


def create_error_message(missing: dict) -> str:
    return "\n".join(
        f"In the {command} command, the following outputs are missing for backward-compatability:"
        f' {",".join(sorted(value))}'
        for command, value in missing.items()
    )


class IsContextPathChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC102"
    description = "Validate that the context path has been changed."
    rationale = "Changing the paths may break dependent content items, which rely on the existing paths."
    error_message = "Changing output context paths is not allowed. Restore the following outputs: {}"
    related_field = "outputs"
    expected_git_statuses = [
        GitStatuses.RENAMED,
        GitStatuses.MODIFIED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(create_error_message(missing)),
                content_object=content_item,
            )
            for content_item in content_items
            if (missing := is_context_path_changed(integration=content_item))
        ]
