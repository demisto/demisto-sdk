
from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.common.tools import get_pack_name
from demisto_sdk.commands.content_graph.objects.base_content import BaseContent
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    GitStatuses,
    ValidationResult,
)

ContentTypes = BaseContent
class PackNameValidator(BaseValidator[ContentTypes]):
    error_code = "BA114"
    description = "Validate that the name of the pack for a content item was not changed."
    error_message = "Pack for a content item '{0}' was changed from '{1}' to '{2}', please undo."
    related_field = "path"
    expected_git_statuses = [GitStatuses.RENAMED]
    new_pack_name = ''
    old_pack_name = ''
    new_path = ''
    
    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    self.new_path,
                    self.old_pack_name,
                    self.new_pack_name,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.pack_has_changed(content_item)
        ]
        
    def pack_has_changed(self, content_item: ContentTypes):
        old_pack_name = get_pack_name(content_item.old_base_content_object.path)
        new_pack_name = get_pack_name(content_item.path)
        name_has_changed = new_pack_name != old_pack_name
        if name_has_changed:
            self.new_pack_name = new_pack_name
            self.old_pack_name = old_pack_name
            self.new_path = content_item.path.parent.relative_to(CONTENT_PATH)
        return name_has_changed
            
