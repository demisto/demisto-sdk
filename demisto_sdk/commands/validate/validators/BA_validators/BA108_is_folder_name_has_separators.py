from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script]


class IsFolderNameHasSeparatorsValidator(BaseValidator[ContentTypes]):
    error_code = "BA108"
    description = "Check if there are separators in the folder name."
    error_message = "The folder name '{0}' should be without any separator."
    related_field = ""
    rationale = "To ensure consistent, readable folder structures by avoiding separators like spaces, underscores, or hyphens."
    is_auto_fixable = False
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.ADDED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        separators = ["_", "-"]
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.path.parent.name),
                content_object=content_item,
            )
            for content_item in content_items
            if (any(char in separators for char in content_item.path.parent.name))
        ]
