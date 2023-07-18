from typing import Tuple, Type
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.classifier import Classifier
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate_poc.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class IDNameValidator(BaseValidator):
    error_code = "YV100"
    description = "Validate that the file id and name fields are identical."
    error_message = "ID and name are not identical."
    is_auto_fixable = True
    related_field = "name"
    content_types = (Integration, Classifier)

    @classmethod
    def is_valid(cls, content_item: ContentItem) -> ValidationResult:
        if content_item.object_id != content_item.name:
            return ValidationResult(
                error_code=cls.error_code, is_valid=False, message=cls.error_message, file_path=content_item.path
            )
        return ValidationResult(error_code=cls.error_code, is_valid=True, message="", file_path=content_item.path)

    @classmethod
    def fix(cls, content_item: ContentItem) -> None:
        content_item.name = content_item.object_id
        with open(content_item.path, "w") as f:
            content_item.handler.dump(content_item.data, f)
