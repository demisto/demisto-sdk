from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import VALID_INDICATOR_TYPE_REGEX
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IndicatorType


# Valid indicator type can include letters, numbers whitespaces, ampersands and underscores.


class IsValidIndicatorTypeId(BaseValidator[ContentTypes]):
    error_code = "RP103"
    description = "Validate that the 'id' field of indicator type has valid value."
    error_message = (
        "The `id` field must consist of alphanumeric characters (A-Z, a-z, 0-9), whitespaces ( ), "
        "underscores (_), and ampersands (&) only."
    )
    rationale = "we want to make sure the id of the indicator type is valid."
    related_field = "id"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.object_id
                and not re.match(VALID_INDICATOR_TYPE_REGEX, content_item.object_id)
            )
        ]
