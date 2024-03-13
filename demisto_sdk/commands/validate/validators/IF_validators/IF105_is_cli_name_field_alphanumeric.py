from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField

FIELD_CLI_NAME_VALIDATION_REGEX = re.compile(r"[0-9a-z]+$")


class IsCliNameFieldAlphanumericValidator(BaseValidator[ContentTypes]):
    error_code = "IF105"
    description = "Checks if cliName field is alphanumeric and lowercase."
    rationale = "`cliName` is not allowed with non-alphanumeric uppercase letters in the platform."
    error_message = "Field `cliName` contains non-alphanumeric or uppercase letters."
    related_field = "cliName"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (not FIELD_CLI_NAME_VALIDATION_REGEX.fullmatch(content_item.cli_name))
        ]
