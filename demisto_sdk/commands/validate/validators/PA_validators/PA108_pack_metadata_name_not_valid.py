from typing import Optional, TypeVar

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = TypeVar("ContentTypes", bound=Pack)

class PackMetadataNameValidator(BaseValidator[ContentTypes]):
    error_code = "PA108"
    description = (
        "Validate that the pack name field exist and is different from the default one."
    )
    error_message = "Pack metadata name field ({}) is missing or invalid. Please fill valid pack name."
    is_auto_fixable = False
    related_field = "pack name"
    content_types = ContentTypes

    def is_valid(
        self, content_item: ContentTypes, old_content_item: Optional[ContentTypes] = None
    ) -> ValidationResult:
        if not content_item.name or "fill mandatory field" in content_item.name:
            return ValidationResult(
                error_code=self.error_code,
                is_valid=False,
                message=self.error_message.format(content_item.name),
                file_path=content_item.path,
            )
        return ValidationResult(
            error_code=self.error_code,
            is_valid=True,
            message="",
            file_path=content_item.path,
        )
