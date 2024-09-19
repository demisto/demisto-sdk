from __future__ import annotations

from typing import Iterable, List, cast

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ContentItem


class IsValidToversionOnModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC107"
    description = (
        "Check that the toversion property was not changed on existing Content files."
    )
    rationale = "Changing the `toversion` field for a content item can break backward compatibility."
    error_message = "Changing the maximal supported version field `toversion` is not allowed. Please undo, or request a force merge."
    related_field = "toversion"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if toversion_modified(content_item)
        ]


def toversion_modified(content_item: ContentTypes) -> bool:
    if not content_item.old_base_content_object:
        return False
    old_file = cast(ContentTypes, content_item.old_base_content_object)
    return content_item.toversion != old_file.toversion
