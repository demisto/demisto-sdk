from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IndicatorType


class ExpirationFieldIsNumericValidator(BaseValidator[ContentTypes]):
    error_code = "RP101"
    description = (
        "Validate that the 'expiration' field has a non-negative integer value."
    )
    rationale = "To align with the platform requirements."
    error_message = "The 'expiration' field should have a non-negative integer value, current is: {0} of type {1}."
    related_field = "expiration"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.expiration, type(content_item.expiration)
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if Version(content_item.fromversion) >= Version("5.5.0")
            and (
                not isinstance(content_item.expiration, int)
                or content_item.expiration < 0
            )
        ]
