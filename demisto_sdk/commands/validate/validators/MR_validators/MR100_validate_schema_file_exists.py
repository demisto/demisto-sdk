from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = ModelingRule


class ValidateSchemaFileExistsValidator(BaseValidator[ContentTypes]):
    error_code = "MR100"
    description = "Validate that each modeling rule has a corresponding schema file."
    rationale = "For each modeling rule, there has to be schema file."
    error_message = 'The modeling rule "{0}" is missing a schema file.'
    related_field = "modeling rule"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.name),
                content_object=content_item,
            )
            for content_item in content_items
            if (not content_item.schema_file.exist)
        ]
