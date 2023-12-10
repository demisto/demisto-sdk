
from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

INDICATOR_FIELD_TYPE_TO_MIN_VERSION = {
    "html": "6.1.0",
    "grid": "5.5.0",
}

ContentTypes = IndicatorField

class IndicaotrFieldFromVersionValidator(BaseValidator[ContentTypes]):
    error_code = "IF112"
    description = "Validate that the indicator fromversion is sufficient according to its type"
    error_message = "The fromversion of IndicatorField with type {0} must be at least {1}, current is {2}."
    fix_message = "Raised the fromversion field to {0}."
    related_field = "fromversion"
    is_auto_fixable = True

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.type, INDICATOR_FIELD_TYPE_TO_MIN_VERSION.get(content_item.content_type, "5.0.0"), content_item.fromversion),
                content_object=content_item,
            )
            for content_item in content_items
            if Version(content_item.fromversion) < Version(INDICATOR_FIELD_TYPE_TO_MIN_VERSION.get(content_item.content_type, "5.0.0"))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        version_to_set: str = INDICATOR_FIELD_TYPE_TO_MIN_VERSION.get(content_item.content_type, "5.0.0")
        content_item.fromversion = version_to_set
        return FixResult(
            validator=self,
            message=self.fix_message.format(version_to_set),
            content_object=content_item
        )
            
