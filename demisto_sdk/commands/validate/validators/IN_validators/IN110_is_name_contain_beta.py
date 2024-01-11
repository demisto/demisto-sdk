from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsIdContainBetaValidator(BaseValidator[ContentTypes]):
    error_code = "IN109"
    description = "Validate that the name field doesn't include the substring 'beta'."
    error_message = (
        "The name field ({0}) contains the word 'beta', make sure to remove it."
    )
    fix_message = "Removed the work 'beta' from the name field, the new name is: ({0})"
    related_field = "name"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_beta and "beta" in content_item.name.lower()
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.name = content_item.name.replace("beta", "")
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.name),
            content_object=content_item,
        )
