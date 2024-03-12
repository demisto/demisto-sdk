from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import CLASSIFICATION_TYPE
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Classifier


class IsValidClassifierTypeValidator(BaseValidator[ContentTypes]):
    error_code = "CL100"
    description = "Validate that a classifier has a type = classification field."
    rationale = "This standardization is for the platform to correctly identify and handle the classifier."
    error_message = f"Classifiers type must be {CLASSIFICATION_TYPE}."
    fix_message = "Changed type to 'classification'."
    related_field = "type"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (content_item.type != CLASSIFICATION_TYPE)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.type = CLASSIFICATION_TYPE
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
