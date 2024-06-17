from __future__ import annotations
import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.content_graph.objects.indicator_type import IndicatorType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IndicatorType

# Valid indicator type can include letters, numbers whitespaces, ampersands and underscores.
VALID_INDICATOR_TYPE = "^[A-Za-z0-9_& ]*$"


class IsValidIndicatorTypeId(BaseValidator[ContentTypes]):
    error_code = "RP103"
    description = "Validate that the 'id' field of indicator type has valid value."
    error_message = "id field contain invalid value."
    related_field = "id"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (content_item.object_id and not re.match(VALID_INDICATOR_TYPE, content_item.object_id))
        ]
