from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.incident_type import IncidentType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentType


class IncidentTypeValidAutoExtractModeValidator(BaseValidator[ContentTypes]):
    error_code = "IT103"
    rationale = (
        "auto extract mode is supposed to be:"
        " 'All' To extract all indicator types regardless of auto-extraction settings."
        "'Specific' - To extract only the specific indicator types set in the auto-extraction settings."
    )
    description = "Check if auto extract mode valid."
    error_message = (
        "The `mode` field under `extractSettings` should be one of the following:\n"
        ' - "All" - To extract all indicator types regardless of auto-extraction settings.\n'
        ' - "Specific" - To extract only the specific indicator types set in the auto-extraction settings.'
    )
    related_field = "extractSettings"

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
                (mode := content_item.extract_settings.get("mode"))
                and mode not in ["All", "Specific"]
            )
        ]
