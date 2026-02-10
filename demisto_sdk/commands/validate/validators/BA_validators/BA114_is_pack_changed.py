from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.common.constants import PACKS_FOLDER
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
    description = (
        "Validate that we didn't move a content item from one pack to another."
    )
    rationale = "Pack of a content item should not be changed."
    error_message = "Pack for content item '{0}' and all related files were changed from '{1}' to '{2}', please undo."
    related_field = "path"
    expected_git_statuses = [GitStatuses.RENAMED]
    new_pack_name = ""
    old_pack_name = ""
    new_path = ""

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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
        old_pack_name = get_pack_name(content_item.old_base_content_object.path)  # type: ignore
        new_pack_name = get_pack_name(content_item.path)
        name_has_changed = new_pack_name != old_pack_name
        if name_has_changed:
            self.new_pack_name = new_pack_name
            self.old_pack_name = old_pack_name
            self.new_path = str(content_item.path).split(PACKS_FOLDER)[-1]
        return name_has_changed
