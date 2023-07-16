from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate_poc.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)


class IDNameValidator(BaseValidator):
    error_code = "YV100"
    error_message = "ID and name are not identical."
    description = "Validate that the file id and name fields are identical."
    related_field = "name"
    is_auto_fixable = True
    # def content_items_to_run(self):
    #     return [ContentType.PACK, ContentType.INTEGRATION]
    @classmethod
    def should_run(cls, content_item: BaseContent) -> bool:
        return content_item.content_type == ContentType.PACK
    @classmethod
    def is_valid(cls, content_item) -> ValidationResult:
        if content_item.object_id != content_item.name:
            return ValidationResult(error_code=cls.error_code, is_valid=False, message=cls.error_message)
        return ValidationResult(error_code=cls.error_code, is_valid=True, message="")
    @classmethod
    def fix(cls, content_item: BaseContent) -> None:
        content_item.object_id = content_item.name
