from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import MarketplaceVersions
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

ContentTypes = Union[
    AgentixAgent,
    AgentixAction,
    Script
]


class IsMarketplaceExistsValidator(BaseValidator[ContentTypes]):
    error_code = "BA130"
    description = f"Content items of type {ContentType.AGENTIX_AGENT}, {ContentType.AGENTIX_ACTION} and {ContentType.SCRIPT} with isLLM=true should be uploaded to xsoar_saas only."
    rationale = "These types of items should be uploaded to xsoar_saas only."
    error_message = f"The items {ContentType.AGENTIX_AGENT}, {ContentType.AGENTIX_ACTION} and {ContentType.SCRIPT} with isLLM=true should be uploaded to xsoar_saas only. Please specify only xsoar_saas under marketplaces."

    def obtain_invalid_content_items(
            self,
            content_items: Iterable[ContentTypes],
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if self.is_invalid_marketplace(content_item)
        ]

    def is_invalid_marketplace(self, content_item: ContentTypes) -> bool:
        if (content_item.content_type in [
            ContentType.AGENTIX_AGENT,
            ContentType.AGENTIX_ACTION,
        ]) or (content_item.content_type == ContentType.SCRIPT and content_item.is_llm):
            return len(content_item.marketplaces) > 1 or len(content_item.marketplaces) == 0 or MarketplaceVersions.PLATFORM.value != content_item.marketplaces[0].value
