from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration]


class IsContextPathChangedValidator(BaseValidator[ContentTypes]):
    error_code = "BC102"
    description = "context path has been changed."
    rationale = "To prevent context paths from changing."
    error_message = "You've changed the context path in the file, please undo."
    related_field = ""
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.RENAMED,
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
    ]
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (self.is_context_path_changed(content_item=content_item))
        ]

    def is_context_path_changed(self, content_item: Integration) -> bool:
        """
        This method checks if an output context path (an integration) is changed.
        """

        new_outputs_context_path = []
        for command in content_item.commands:
            new_outputs_context_path.extend(command.get_outputs_context_path())

        old_outputs_context_path = []
        for (
            command
        ) in content_item.old_base_content_object.commands:  # type:ignore[union-attr]
            old_outputs_context_path.extend(command.get_outputs_context_path())

        return not set(old_outputs_context_path).issubset(set(new_outputs_context_path))
