
from __future__ import annotations

from typing import Dict, Iterable, List

from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Pack

class PackNameValidator(BaseValidator[ContentTypes]):
    error_code = "BA114"
    description = "Validate that the name of the pack was not changed."
    error_message = "Pack name was changed from {0} to {1}, please undo."
    # fix_message = "Changing pack name back to {0}."
    related_field = "path"
    # is_auto_fixable = True
    new_pack_name: str = ''
    old_pack_name: str = ''

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    self.old_pack_name,
                    self.new_pack_name,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if self.pack_name_has_changed(content_item)
        ]
        
    def pack_name_has_changed(self, content_item: ContentTypes):
        old_path_to_pack_metadata = str(content_item.old_base_content_object.path) #type: ignore
        new_path_to_pack_metadata = str(content_item.path)
        old_pack_name = old_path_to_pack_metadata.split('/')[-1]
        new_pack_name = new_path_to_pack_metadata.split('/')[-1]
        name_has_changed = new_pack_name != old_pack_name
        if name_has_changed:
            self.new_pack_name = new_pack_name
            self.old_pack_name = old_pack_name
        return name_has_changed

    # def fix(self, content_item: ContentTypes) -> FixResult:
    #     content_item.name = self.old_name[content_item.name]
    #     return FixResult(
    #         validator=self,
    #         message=self.fix_message.format(content_item.name),
    #         content_object=content_item,
    #     )
            
