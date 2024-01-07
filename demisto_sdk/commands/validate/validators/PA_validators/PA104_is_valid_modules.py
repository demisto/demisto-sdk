from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import MODULES
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class IsValidModulesValidator(BaseValidator[ContentTypes]):
    error_code = "PA104"
    description = "Validate that the modules field include only labels from the list of allowed labels."
    error_message = f"Module field can include only label from the following options: {', '.join(MODULES)}."
    related_field = "modules"
    is_auto_fixable = True
    fix_message = "Removed the following label from the modules field: {0}."

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not set(content_item.modules).issubset(MODULES)  # type: ignore[union-attr, arg-type]
        ]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        not_approved_labels = [
            module for module in content_item.modules if module not in MODULES  # type: ignore[union-attr, arg-type]
        ]
        content_item.modules = [
            module for module in content_item.modules if module in MODULES  # type: ignore[union-attr, arg-type]
        ]
        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(not_approved_labels)),
            content_object=content_item,
        )
