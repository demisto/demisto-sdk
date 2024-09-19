from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsDisplayContainBetaValidator(BaseValidator[ContentTypes]):
    error_code = "IN112"
    description = "Validate that the display name contain the substring 'beta'."
    rationale = "Beta integrations should have 'beta' in the display name for clear identification and to manage user expectations."
    error_message = (
        "The display name ({0}) doesn't contain the word 'beta', make sure to add it."
    )
    related_field = "display"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.display_name),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_beta and "beta" not in content_item.display_name.lower()
        ]
