from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class PackMetadataNameValidator(BaseValidator[ContentTypes]):
    error_code = "PA108"
    description = (
        "Validate that the pack name field exist and is different from the default one."
    )
    rationale = "A unique and meaningful pack name is crucial for identifying the pack and its contents."
    error_message = "Pack metadata name field is either missing or invalid. Please fill valid pack name."
    related_field = "pack name"
    is_auto_fixable = False

    def is_valid(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not content_item.name
            or content_item.name.isspace()
            or "fill mandatory field" in content_item.name
        ]
