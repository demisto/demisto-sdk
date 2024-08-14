from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[CaseField, IncidentField]

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
    description = "Checks if given field type is valid."
    rationale = "The types of the IncidentField are limited by the platform."
    error_message = "Type: `{file_type}` is not one of available types.\navailable types: {type_fields}."
    related_field = "type"

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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
