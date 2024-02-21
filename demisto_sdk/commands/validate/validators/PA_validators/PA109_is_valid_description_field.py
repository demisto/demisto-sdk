from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsValidDescriptionFieldValidator(BaseValidator[ContentTypes]):
    error_code = "PA109"
    description = "Validate that the metadata description field isn't empty and is different from the default one."
    rationale = (
        "A unique and meaningful pack description is crucial for identifying the pack, "
        "understanding its purpose, and differentiating it from other packs."
    )
    error_message = "Pack metadata description field is invalid. Please fill valid pack description."
    related_field = "description"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.description
            or "fill mandatory field" in content_item.description
        ]
