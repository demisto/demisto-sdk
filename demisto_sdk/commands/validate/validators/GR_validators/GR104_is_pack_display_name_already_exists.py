from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Pack


class IsPackDisplayNameAlreadyExistsValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR104"
    description = (
        "Validate that there are no duplicate display names of packs in the repo"
    )
    rationale = "Prevent confusion between packs."
    error_message = (
        "Pack '{content_id}' has a duplicate display_name as: {pack_display_id}."
    )
    related_field = ""
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        file_paths_to_objects = {
            str(content_item.path.relative_to(CONTENT_PATH)): content_item
            for content_item in content_items
        }
        content_id_to_objects = {item.object_id: item for item in content_items}  # type: ignore[attr-defined]

        query_list = list(file_paths_to_objects) if not validate_all_files else []

        query_results = self.graph.get_duplicate_pack_display_name(query_list)

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_id=content_id,
                    pack_display_id=(", ".join(duplicate_names_id)),
                ),
                content_object=content_id_to_objects[content_id],
            )
            for content_id, duplicate_names_id in query_results
            if content_id in content_id_to_objects
        ]
