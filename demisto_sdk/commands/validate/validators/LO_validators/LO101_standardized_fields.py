from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects import LayoutRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[LayoutRule]


class LayoutRuleStandardizedFieldsValidator(BaseValidator[ContentTypes]):
    error_code = "LO101"
    description = "Validate that Layout Rules use standardized 'id' and 'name' fields instead of 'rule_id' and 'rule_name'."
    rationale = "New content items should use standardized field names 'id' and 'name' for consistency across all content types."
    error_message = "Layout Rules must use 'id' and 'name' fields instead of 'rule_id' and 'rule_name'. Please update your layout rule to use the standardized field names."
    related_field = "rule_id, rule_name"
    is_auto_fixable = False

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
            if self.has_non_standard_fields(content_item)
        ]

    def has_non_standard_fields(self, content_item: ContentTypes) -> bool:
        """Check if the content item uses non-standard field names."""
        data = content_item.data

        # Check for non-standard fields
        has_rule_id = "rule_id" in data
        has_rule_name = "rule_name" in data
        has_standard_id = "id" in data
        has_standard_name = "name" in data

        # Invalid if it has old fields but not the corresponding new standard fields
        return (has_rule_id and not has_standard_id) or (has_rule_name and not has_standard_name)
