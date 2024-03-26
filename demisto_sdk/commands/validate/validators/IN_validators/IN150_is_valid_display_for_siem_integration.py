from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsValidDisplayForSiemIntegrationValidator(BaseValidator[ContentTypes]):
    error_code = "IN150"
    description = (
        "Validate that a siem integration display name ends with 'Event Collector'"
    )
    rationale = (
        "This consistent naming convention ensures that users can easily understand what the integration is used for. "
        "For more info see https://xsoar-pan-dev--pull-request-1503-8bvdsez5.web.app/docs/integrations/event-collectors#naming-convention"
    )
    error_message = "The integration is a siem integration with invalid display name ({0}). Please make sure the display name ends with 'Event Collector'"
    fix_message = "Added the 'Event Collector' suffix to the display name, the new display name is {0}."
    related_field = "display, script.isfetchevents"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.display_name),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_fetch_events
            and not content_item.display_name.endswith("Event Collector")
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.display_name = f"{content_item.display_name} Event Collector"
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.display_name),
            content_object=content_item,
        )
