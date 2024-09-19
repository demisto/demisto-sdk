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
    error_message = (
        "The folder name '{0}' should not contain any of the following separators: {1}"
    )
    related_field = "file path"
    rationale = "To ensure consistent, readable folder structures by avoiding separators like spaces, underscores, or hyphens."
    expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.ADDED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        separators = ["_", "-"]
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.path.parent.name,
                    ", ".join(f"'{sep}'" for sep in separators),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                any(
                    separator in content_item.path.parent.name
                    for separator in separators
                )
            )
        ]
