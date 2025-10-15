from __future__ import annotations

from abc import ABC
from typing import Iterable, List

from demisto_sdk.commands.common.content_constant_paths import CONTENT_PATH
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = AgentixAction


class IsAgentixActionNameAlreadyExistsValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR112"
    description = (
        "Validate that there are no duplicate names of Agentix Actions in the repo."
    )
    rationale = "Prevent confusion between Agentix Actions."
    error_message = (
        "Agentix Action '{content_id}' has a duplicate name as: {duplicate_name_ids}."
    )
    related_field = "name"
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

        query_results = self.graph.validate_duplicate_agentix_action_names(query_list)

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_id=content_id,
                    duplicate_display_name_ids=(", ".join(duplicate_name_ids)),
                ),
                content_object=content_id_to_objects[content_id],
            )
            for content_id, duplicate_name_ids in query_results
            if content_id in content_id_to_objects
        ]
