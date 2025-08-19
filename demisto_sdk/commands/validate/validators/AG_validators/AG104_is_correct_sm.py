from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses, PlatformSupportedModules
from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects import (
    AgentixAction,
    AgentixAgent,
)
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[AgentixAgent, AgentixAction, Script]


class IsCorrectSMValidator(BaseValidator[ContentTypes]):
    error_code = "AG104"
    description = f"Content items of type {', '.join(filter(None, [ContentType.AGENTIX_AGENT, ContentType.AGENTIX_ACTION, ContentType.SCRIPT]))} with isllm=True should be uploaded to agentix supported modules only."
    rationale = (
        "These types of items should be uploaded to agentix supported modules only."
    )
    error_message = "The following Agentix related content item '{0}' should have only 'agentix' type supportedModules. Valid modules - {1}"
    expected_git_statuses = [
        GitStatuses.ADDED,
        GitStatuses.MODIFIED,
        GitStatuses.RENAMED,
    ]
    agentix_modules = {
        PlatformSupportedModules.AGENTIX.value,
        PlatformSupportedModules.AGENTIX_XSIAM.value,
    }

    def obtain_invalid_content_items(
        self,
        content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.display_name, self.agentix_modules
                ),
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
            ]
        ) or (content_item.content_type == ContentType.SCRIPT and content_item.is_llm):  # type: ignore
            current_supportedModules = (
                content_item.supportedModules if content_item.supportedModules else []
            )
            return len(current_supportedModules) == 0 or not set(
                current_supportedModules
            ).issubset(self.agentix_modules)
        return False
