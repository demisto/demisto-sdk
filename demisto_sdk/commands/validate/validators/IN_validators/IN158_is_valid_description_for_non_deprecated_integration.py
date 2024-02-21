from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    DEPRECATED_DESC_REGEX,
    DEPRECATED_NO_REPLACE_DESC_REGEX,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidDescriptionForNonDeprecatedIntegrationValidator(
    BaseValidator[ContentTypes]
):
    error_code = "IN158"
    description = "Validate that the description for non-deprecated integrations is not in the deprecation format"
    rationale = (
        "This avoids confusion and ensures that users are correctly informed about the integration's status. "
        "For more about deprecation see: https://xsoar.pan.dev/docs/reference/articles/deprecation-process-and-hidden-packs#how-to-deprecate-an-integration"
    )
    error_message = "All integrations whose description states are deprecated, must have `deprecated:true`.\nPlease run demisto-sdk format --deprecate -i {0}"
    related_field = "deprecated, description"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(str(content_item.path)),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.deprecated
            and content_item.description
            and any(
                (
                    re.search(DEPRECATED_DESC_REGEX, content_item.description),
                    re.search(
                        DEPRECATED_NO_REPLACE_DESC_REGEX, content_item.description
                    ),
                )
            )
        ]
