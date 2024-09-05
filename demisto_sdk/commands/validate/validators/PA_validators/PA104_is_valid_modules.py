from __future__ import annotations

from typing import ClassVar, Iterable, List

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
    rationale = (
        f"See the list of allowed modules in the platform: {', '.join(MODULES)}."
    )
    error_message = f"Module field can include only label from the following options: {', '.join(MODULES)}."
    related_field = "modules"
    is_auto_fixable = True
    fix_message = "Removed the following label from the modules field: {0}."
    non_approved_modules_dict: ClassVar[dict] = {}

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(", ".join(non_approved_modules)),
                content_object=content_item,
            )
            for content_item in content_items
            if (non_approved_modules := self.get_non_approved_modules(content_item))
        ]

    def get_non_approved_modules(self, content_item: ContentTypes):
        self.non_approved_modules_dict[content_item.name] = [
            module for module in content_item.modules if module not in MODULES
        ]
        return self.non_approved_modules_dict[content_item.name]

    def fix(
        self,
        content_item: ContentTypes,
    ) -> FixResult:
        content_item.modules = [
            module
            for module in content_item.modules
            if module not in self.non_approved_modules_dict[content_item.name]  # type: ignore[union-attr, arg-type]
        ]
        return FixResult(
            validator=self,
            message=self.fix_message.format(
                ", ".join(self.non_approved_modules_dict[content_item.name])
            ),
            content_object=content_item,
        )
