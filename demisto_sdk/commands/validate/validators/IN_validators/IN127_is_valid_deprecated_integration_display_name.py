from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidDeprecatedIntegrationDisplayNameValidator(BaseValidator[ContentTypes]):
    error_code = "IN127"
    description = (
        "Validate that a deprecated integration display name ends with (Deprecated)."
    )
    rationale = (
        "Deprecated integrations should end with (Deprecated) in the display name to clearly indicate their status. "
        "This prevents inadvertent use of unsupported integrations. "
        "For more details, see https://xsoar.pan.dev/docs/reference/articles/deprecation-process-and-hidden-packs#how-to-deprecate-an-integration"
    )
    error_message = "The integration is deprecated, make sure the display name ({0}) ends with (Deprecated)."
    fix_message = "Added the (Deprecated) suffix to the integration display name: {0}."
    related_field = "display"
    is_auto_fixable = True

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
            if content_item.deprecated
            and not content_item.display_name.endswith("(Deprecated)")
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.display_name = f"{content_item.display_name} (Deprecated)"
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.display_name),
            content_object=content_item,
        )
