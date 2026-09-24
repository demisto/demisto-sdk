from __future__ import annotations

from abc import ABC
from typing import Iterable, List, Union

from demisto_sdk.commands.common.tools import get_relative_path_from_packs_dir
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.agentix_action import AgentixAction
from demisto_sdk.commands.content_graph.objects.agentix_agent import AgentixAgent
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAction, AgentixAgent]


class DuplicateAgentixActionIdValidator(BaseValidator[ContentTypes], ABC):
    """Temporary validator, replacing GR105 for AgentixAction and AgentixAgent items only.

    AgentixAction and AgentixAgent items with duplicate IDs already exist in the
    private content repo, and are planned to be fixed by December. Until then,
    GR105 skips these items and this validator reports them as a warning, so GR105
    itself can remain an error for all other content types.
    """

    error_code = "GR117"
    description = "Ensures that each Agentix Action and Agentix Agent has a unique ID to prevent conflicts."
    rationale = "Duplicate IDs can cause conflicts and confusion."
    error_message = "Duplicate ID '{}' found in {}"
    related_field = "id"
    is_auto_fixable = False

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        paths_of_content_items_to_validate = (
            []
            if validate_all_files
            else [
                get_relative_path_from_packs_dir(str(content_item.path))
                for content_item in content_items
            ]
        )
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.object_id,
                    get_relative_path_from_packs_dir(str(duplicate.path)),
                ),
                content_object=content_item,  # type: ignore[arg-type]
            )
            for content_item, duplicates in self.graph.validate_duplicate_ids(
                paths_of_content_items_to_validate
            )
            if content_item.content_type
            in (ContentType.AGENTIX_ACTION, ContentType.AGENTIX_AGENT)
            for duplicate in duplicates
        ]
