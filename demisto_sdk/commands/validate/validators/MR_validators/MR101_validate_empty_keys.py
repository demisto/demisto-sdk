from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


class ValidateEmptyKeysValidator(BaseValidator[ContentTypes]):
    error_code = "MR101"
    description = 'Validate that the modeling rules keys - "rules" and "schema" exist and are empty'
    rationale = "This validation is for compatibility resaons. Without those fields the modeling rules won't work."
    error_message = (
        "Either the 'rules' key or the 'schema' key are missing or not empty, "
        "make sure to set the values of these keys to an empty string."
    )
    related_field = "modeling rule"

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
            if content_item.schema_key != "" or content_item.rules_key != ""
        ]
