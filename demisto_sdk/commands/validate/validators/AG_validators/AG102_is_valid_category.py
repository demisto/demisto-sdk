from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.common.tools import get_current_categories
from demisto_sdk.commands.content_graph.objects import AgentixAction, AgentixAgent
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAction, AgentixAgent]


class IsValidCategoryValidator(BaseValidator[ContentTypes]):
    error_code = "AG102"
    description = "Validate that the Agentix-items category is valid."
    rationale = (
        "See the list of allowed categories in the platform: "
        "https://xsoar.pan.dev/docs/documentation/pack-docs#pack-keywords-tags-use-cases--categories"
    )
    error_message = (
        "The Agentix-item '{0}' category '{1}' doesn't match the standard,\n"
        "please make sure that the field is a category from the following options: {2}."
    )
    related_field = "category"
    is_auto_fixable = False
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        approved_list = get_current_categories()
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name,
                    content_item.category,
                    ", ".join(approved_list),
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.category and content_item.category not in approved_list
        ]
