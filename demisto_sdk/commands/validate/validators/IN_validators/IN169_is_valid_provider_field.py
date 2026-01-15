from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidProviderFieldValidator(BaseValidator[ContentTypes]):
    error_code = "IN169"
    description = "Validate that the Integration has a provider field with a value."
    rationale = (
        "The provider field is required to identify the service provider for the integration."
    )
    error_message = "The Integration is missing the 'provider' field or it has an empty value. Please add a valid provider name."
    related_field = "provider"
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
            if not content_item.provider or not content_item.provider.strip()
        ]
