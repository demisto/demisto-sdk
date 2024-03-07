from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MarketplaceVersions
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class ShouldIncludeModulesValidator(BaseValidator[ContentTypes]):
    error_code = "PA105"
    description = (
        "Validate that the pack has the marketplacev2 label if it include modules."
    )
    rationale = "This field is only used in XSIAM."
    error_message = "Module field can be added only for XSIAM packs (marketplacev2)."
    fix_message = "Emptied the modules field."
    related_field = "modules"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.modules
            and MarketplaceVersions.MarketplaceV2 not in content_item.marketplaces
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.modules = []
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
