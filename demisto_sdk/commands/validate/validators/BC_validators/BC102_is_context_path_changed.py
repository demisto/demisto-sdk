from __future__ import annotations

from itertools import chain
from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


def is_context_path_changed(content_item: Integration) -> bool:
    """
    This method checks if an output context path (an integration) is changed.
    """

    new_outputs_context_path = set(
        chain.from_iterable(
            command.outputs_context_paths for command in content_item.commands
        )
    )

    old_outputs_context_path = set(
        chain.from_iterable(
            command.outputs_context_paths
            # Since old_base_content_object is an integration, we ignore the mypy comment
            for command in content_item.old_base_content_object.commands  # type:ignore[union-attr]
        )
    )

    return not old_outputs_context_path.issubset(new_outputs_context_path)


class IsContextPathChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC102"
    description = "Validate that the context path has been changed."
    rationale = "Changing the paths may break dependent content items, which rely on the existing paths."
    error_message = "Changing output context paths is not allowed."
    related_field = "outputs"
    expected_git_statuses = [
        GitStatuses.RENAMED,
        GitStatuses.MODIFIED,
    ]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (is_context_path_changed(content_item=content_item))
        ]
