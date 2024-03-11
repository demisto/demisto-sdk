from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.tools import get_current_categories
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidCategoryValidator(BaseValidator[ContentTypes]):
    error_code = "IN104"
    description = "Validate that the Integrations category is valid."
    rationale = (
        "See the list of allowed categories in the platform: "
        "https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    )
    error_message = "The Integration's category ({0}) doesn't match the standard,\nplease make sure that the field is a category from the following options: {1}."
    related_field = "category"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        approved_list = get_current_categories()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.category or "empty category section",
                    ", ".join(approved_list),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.category not in approved_list
        ]
