from __future__ import annotations

import re
from typing import Iterable, List

from demisto_sdk.commands.common.constants import RelatedFileType
from demisto_sdk.commands.content_graph.objects.incident_field import IncidentField
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = IncidentField

FIELD_CLI_NAME_VALIDATION_REGEX = re.compile(r"[0-9a-z]+$")


class IsCliNameFieldAlphanumericValidator(BaseValidator[ContentTypes]):
    error_code = "IF105"
    description = "Validate the cliName field is alphanumeric"
    error_message = "Field `cliName` contains non-alphanumeric letters"
    related_field = "cliName"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.JSON]

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
