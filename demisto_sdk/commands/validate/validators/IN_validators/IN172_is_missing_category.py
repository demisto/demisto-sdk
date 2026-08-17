from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsMissingCategoryValidator(BaseValidator[ContentTypes]):
    error_code = "IN172"
    description = "Validate that the integration has a category field."
    rationale = (
        "The category field is required for integrations so they can be grouped "
        "and discovered correctly in the platform."
    )
    error_message = "The integration is missing a category field. Please make sure to add a category."
    related_field = "category"
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
            if not content_item.category
        ]
