from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses, MarketplaceVersions
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import (
    AgentixAction,
    AgentixAgent,
    AIPrompt,
)
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAgent, AgentixAction, AIPrompt, Script]


class IsCorrectMPValidator(BaseValidator[ContentTypes]):
    error_code = "AG101"
    description = f"Content items of type {', '.join(filter(None, [ContentType.AGENTIX_AGENT, ContentType.AGENTIX_ACTION, ContentType.AIPROMPT, ContentType.SCRIPT]))} with isllm=true should be uploaded to platform only."
    rationale = "These types of items should be uploaded to platform only."
    error_message = "The following Agentix related content item '{0}' should have only marketplace 'platform'."
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
            if self.is_invalid_marketplace(content_item)
        ]

    def is_invalid_marketplace(self, content_item: ContentTypes) -> bool:
        if (
            content_item.content_type
            in [
                ContentType.AGENTIX_AGENT,
                ContentType.AGENTIX_ACTION,
                ContentType.AIPROMPT,
            ]
        ) or (content_item.content_type == ContentType.SCRIPT and content_item.is_llm):  # type: ignore
            return (
                len(content_item.marketplaces) > 1
                or len(content_item.marketplaces) == 0
                or MarketplaceVersions.PLATFORM.value
                != content_item.marketplaces[0].value
            )
        return False
