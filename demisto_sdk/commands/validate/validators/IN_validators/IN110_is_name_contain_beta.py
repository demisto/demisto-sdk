from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsNameContainBetaValidator(BaseValidator[ContentTypes]):
    error_code = "IN110"
    description = "Validate that the name field doesn't include the substring 'beta'."
    rationale = "The name field in an integration should not contain the word 'beta'. This ensures unambiguous identification of production-ready integrations."
    error_message = (
        "The name field ({0}) contains the word 'beta', make sure to remove it."
    )
    fix_message = "Removed the word 'beta' from the name field, the new name is: {0}."
    related_field = "name"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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
        content_item.name = re.sub(
            "[ \t]+", " ", content_item.name.replace("beta", "")
        ).strip()
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.name),
            content_object=content_item,
        )
