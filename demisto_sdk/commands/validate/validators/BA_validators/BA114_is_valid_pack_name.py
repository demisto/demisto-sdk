
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import GitStatuses, RelatedFileType
from demisto_sdk.commands.common.tools import get_pack_name
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack


class PackNameValidator(BaseValidator[ContentTypes]):
    error_code = "BA114"
    description = "Checks if pack's name was changed"
    error_message = "You've changed the pack name, please use"
    # fix_message = "fixing the pack name"
    related_field = "name"
    is_auto_fixable = True
    # expected_git_statuses = [GitStatuses.RENAMED, GitStatuses.MODIFIED, GitStatuses.ADDED]
    related_file_type = [RelatedFileType.CODE]

    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if (
                content_item.pack_name == ''
            )
        ]
    

    def fix(self, content_item: ContentTypes) -> FixResult:
        # Add your fix right here
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
            
