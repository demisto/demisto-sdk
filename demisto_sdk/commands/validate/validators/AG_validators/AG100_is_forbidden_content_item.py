from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import (
    AgentixAction,
    AgentixAgent,
    Script,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAgent, AgentixAction, Script]


class IsForbiddenContentItemValidator(BaseValidator[ContentTypes]):
    error_code = "AG100"
    description = "We should not push these items to the Content repository."
    rationale = "These types of items should be stored in a private repository."
    error_message = "The following Agentix related content item '{0}' should not be uploaded through content repo, please move it to content-test-conf repo."
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.display_name),
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_invalid_item(content_item)
        ]

    def is_invalid_item(self, content_item: ContentTypes) -> bool:
        return content_item.content_type in [
            ContentType.AGENTIX_AGENT,
            ContentType.AGENTIX_ACTION,
        ] or (content_item.content_type == ContentType.SCRIPT and content_item.is_llm)  # type: ignore
