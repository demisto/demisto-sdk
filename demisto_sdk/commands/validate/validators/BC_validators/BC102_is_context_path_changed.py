from __future__ import annotations

from typing import Iterable, List, Optional, Set

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


def is_context_path_changed(integration: Integration) -> dict[str, Set[Optional[str]]]:
    """
    This method returns the diff between the integrations versions per command.
    """
    result = defaultdict(set)
    old_integration = integration.old_base_content_object
    mapping_old_commands = {
        # Since we're sure old_integration has 'commands' attribute, we ignore it (down casting does not solve it)
        command.name: command
        for command in old_integration.commands  # type:ignore[union-attr]
    }
    mapping_new_commands = {command.name: command for command in integration.commands}
    for command in sorted(set(mapping_new_commands).intersection(mapping_old_commands)):
            if diff := mapping_new_commands[command].diff_outputs_context_path(
                mapping_old_commands[command]
            ):
                final_diff[command] = diff

    return final_diff


def create_error_message(missing: dict) -> str:
    return "\n".join(
        f'In the {command} command, the following outputs are missing for backward-compatability: {",".join(sorted(value))}'
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

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(create_error_message(missing)),
                content_object=content_item,
            )
            for content_item in content_items
            if (missing := is_context_path_changed(integration=content_item))
        ]
