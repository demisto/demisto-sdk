from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import (
    PARTNER_SUPPORT,
    SUPPORT_LEVEL_HEADER,
    XSOAR_SUPPORT,
)
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class IsPartnerCollectorHasXsoarSupportLevelValidator(BaseValidator[ContentTypes]):
    error_code = "IN162"
    description = "Validate that the support level header for a collector integration in a Partner pack is set to Xsoar."
    rationale = (
        "Collector integrations in Partner packs should specify {XSOAR_SUPPORT} level support "
        "to accurately inform users about the support level provided by Cortex XSOAR. "
        "For more information about 'support level header' see https://xsoar.pan.dev/docs/documentation/integration-description#support-level-header-yml-metadata-key."
    )
    error_message = f"The integration is a fetch events/assets integration in a partner supported pack.\nTherefore, it should have the key {SUPPORT_LEVEL_HEADER} = {XSOAR_SUPPORT} in its yml."
    related_field = (
        "supportlevelheader, script.isfetchevents, script.isfetcheventsandassets"
    )
    is_auto_fixable = True
    fix_message = f"Changed the integration's should {SUPPORT_LEVEL_HEADER} key to {XSOAR_SUPPORT}."

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.display_name),
                content_object=content_item,
            )
            for content_item in content_items
            if any(
                [
                    content_item.is_fetch_events,
                    content_item.is_fetch_events_and_assets,
                ]
            )
            and (
                content_item.support_level == PARTNER_SUPPORT
                and content_item.data.get(SUPPORT_LEVEL_HEADER) != XSOAR_SUPPORT
            )
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.data[SUPPORT_LEVEL_HEADER] = XSOAR_SUPPORT
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.display_name),
            content_object=content_item,
        )
