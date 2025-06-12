from __future__ import annotations

from abc import ABC

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects import AgentixAgent, AgentixAction
from demisto_sdk.commands.content_graph.parsers.related_files import RelatedFileType
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    AgentixAgent,
    AgentixAction
]


class IsAgentixActionUsingExistingContentItemValidator(BaseValidator[ContentTypes], ABC):
    error_code = "GR110"
    description = ""
    rationale = ""
    error_message = ""
    related_field = ""
    is_auto_fixable = False
    # expected_git_statuses = [GitStatuses.ADDED, GitStatuses.MODIFIED]
    related_file_type = [RelatedFileType.README]

    def obtain_invalid_content_items_using_graph(
        self, content_items: Iterable[ContentTypes], validate_all_files: bool
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            name = content_item.underlying_content_item_name
            type_content_item = content_item.underlying_content_item_type
            result = self.graph.search(object_id='ad-disable-account')  # TODO - if result is an empty list that means item does not exist
            print("ksahfsa")

        return results
