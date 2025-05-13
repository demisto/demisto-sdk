from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType

from demisto_sdk.commands.content_graph.objects import (
    AgentixAgent,
    AgentixAction,
)

from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[
    AgentixAgent,
    AgentixAction
]


class IsForbiddenContentItemValidator(BaseValidator[ContentTypes]):
    error_code = "BA129"
    description = "We should not push these items to the Content repository."
    rationale = "These types of items should be stored in a private repository."
    error_message = f"The items {ContentType.AGENTIX_AGENT} and {ContentType.AGENTIX_ACTION}" \
                    f" should be stored in content-test-conf, not in Content"

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
            if self.is_invalid_item(content_item)
        ]

    def is_invalid_item(self, content_item: ContentTypes) -> bool:
        return content_item.content_type in [
            ContentType.AGENTIX_AGENT,
            ContentType.AGENTIX_ACTION,
        ]
