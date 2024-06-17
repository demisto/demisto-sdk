from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.modeling_rule import ModelingRule
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = ModelingRule


class ValidateEmptyKeysValidator(BaseValidator[ContentTypes]):
    error_code = "MR101"
    description = (
        "Validate that the modeling rules keys - rules and schema exist and are empty"
    )
    rationale = "This standardization is to handle modeling rules correctly."
    error_message = (
        "Either the 'rules' key or the 'schema' key are missing or not empty, "
        "make sure to set the values of these keys to an empty string"
    )
    fix_message = "Updated the keys 'rules' and 'schema' to be an empty string"
    related_field = "modeling rule"
    is_auto_fixable = True
    expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if ("rules" not in content_item.dict().keys())
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
