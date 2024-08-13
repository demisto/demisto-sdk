from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsValidDisplayNameForNonDeprecatedIntegrationValidator(
    BaseValidator[ContentTypes]
):
    error_code = "IN160"
    description = "Validate that the display name for non-deprecated integration doesn't end with '(Deprecated)'."
    rationale = (
        "This ensures accurate representation of the integration's status, avoiding confusion for users "
        "For more about deprecation see: https://xsoar.pan.dev/docs/reference/articles/deprecation-process-and-hidden-packs#how-to-deprecate-an-integration"
    )
    error_message = "All integrations whose display_names end with `(Deprecated)` must have `deprecated:true`.\nPlease run demisto-sdk format --deprecate -i {0}"
    related_field = "deprecated, display"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(str(content_item.path)),
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.deprecated
            and content_item.display_name.endswith("(Deprecated)")
        ]
