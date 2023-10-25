from typing import Optional, TypeVar

from demisto_sdk.commands.common.constants import ADDED, MODIFIED
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixingResult,
    ValidationResult,
)


class BCSubtypeValidator(BaseValidator):
    error_code = "BC100"
    description = (
        "Validate that the pack name subtype of the new file matches the old one."
    )
    error_message = "Possible backwards compatibility break, You've changed the subtype, please undo."
    is_auto_fixable = True
    related_field = "subtype"
    ContentTypes = TypeVar("ContentTypes", Integration, Script)
    fixing_message = "Changing subtype back to the old one ({0})."
    expected_git_statuses = [ADDED, MODIFIED]

    @classmethod
    def is_valid(
        cls, content_item: ContentTypes, old_content_item: Optional[ContentTypes] = None
    ) -> ValidationResult:
        if old_content_item and content_item.type != old_content_item.type:
            return ValidationResult(
                error_code=cls.error_code,
                is_valid=False,
                message=cls.error_message.format(content_item.name),
                file_path=content_item.path,
            )
        return ValidationResult(
            error_code=cls.error_code,
            is_valid=True,
            message="",
            file_path=content_item.path,
        )

    @classmethod
    def fix(
        cls, content_item: ContentTypes, old_content_item: ContentTypes = None
    ) -> FixingResult:
        if old_content_item:
            content_item.type = old_content_item.type
            content_item.save()
            return FixingResult(
                error_code=cls.error_code,
                message=cls.fixing_message.format(old_content_item.type),
                file_path=content_item.path,
            )
