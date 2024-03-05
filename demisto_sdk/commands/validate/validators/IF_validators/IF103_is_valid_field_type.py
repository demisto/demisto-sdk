from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField

FIELD_TYPES = {
    "shortText",
    "longText",
    "boolean",
    "singleSelect",
    "multiSelect",
    "date",
    "user",
    "role",
    "number",
    "attachments",
    "tagsSelect",
    "internal",
    "url",
    "markdown",
    "grid",
    "timer",
    "html",
}


class IsValidFieldTypeValidator(BaseValidator[ContentTypes]):
    error_code = "IF103"
    description = "Checks if given field type is valid"
    error_message = "Type: `{file_type}` is not one of available types.\navailable types: {type_fields}"
    related_field = "type"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.JSON]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    file_type=content_item.field_type, type_fields=FIELD_TYPES
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (content_item.field_type not in FIELD_TYPES)
        ]
