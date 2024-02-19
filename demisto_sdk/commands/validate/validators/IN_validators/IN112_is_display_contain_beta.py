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
    rationale = (
        "If an integration is in its beta stage (as indicated by the 'beta' field in the integration yml being set to true), "
        "its display name should contain the word 'beta'. This practice ensures clear identification of beta integrations, "
        "helping users to understand the integration's development stage and use it accordingly. "
        "Without the 'beta' keyword in the display name, users might not realize that the integration is in a beta stage, "
        "which could lead to unexpected issues or misunderstandings about the integration's stability and feature completeness."
    )
    error_message = (
        "The display name ({0}) doesn't contain the word 'beta', make sure to add it."
    )
    related_field = "display"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.display_name),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_beta and "beta" not in content_item.display_name.lower()
        ]
