from __future__ import annotations

from typing import Iterable, List, cast, Union

from demisto_sdk.commands.common.constants import GitStatuses
# from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.content_graph.objects.parsing_rule import ParsingRule
from demisto_sdk.commands.content_graph.objects.correlation_rule import CorrelationRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[ModelingRule, ParsingRule, CorrelationRule]


class IsValidToversionOnModifiedValidator(BaseValidator[ContentTypes]):
    error_code = "BC115"
    description = (
        "Check that the toversion property is valid."
    )
    rationale = "Changing the `toversion` field for a content item should include adding a new item to replace it."
    error_message = "Changing the maximal supported version field `toversion` is not valid. No new item to replace it."
    related_field = "toversion"
    expected_git_statuses = [GitStatuses.MODIFIED, GitStatuses.RENAMED, GitStatuses.ADDED]  # todo: do we need renamed?

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        modified_items, new_items = sort_content_items(content_items)
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in modified_items
            if not self.toversion_valid(content_item, new_items)
        ]

    def toversion_valid(self, modified_item: ContentTypes, new_items: Iterable[ContentTypes]):
        old_file = cast(ContentTypes, modified_item.old_base_content_object)
        if modified_item.toversion != old_file.toversion:
            return False
        return True

def sort_content_items(content_items: Iterable[ContentTypes]):
    modified_items = []
    new_items = []
    for item in content_items:
        if item.git_status == GitStatuses.MODIFIED:
            modified_items.append(item)
        elif item.git_status == GitStatuses.ADDED:
            new_items.append(item)

    return modified_items, new_items
