from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.case_field import CaseField
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[CaseField, IncidentField]


class IsCliNameFieldAlphanumericValidator(BaseValidator[ContentTypes]):
    error_code = "IF105"
    description = "Checks if cliName field is alphanumeric and lowercase."
    rationale = "Required by the platform."
    error_message = "Field `cliName` contains uppercase or non-alphanumeric symbols."
    related_field = "cliName"

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
            if not (
                content_item.cli_name.isalnum()
                and content_item.cli_name.lower() == content_item.cli_name
            )
        ]
