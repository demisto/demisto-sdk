from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Integration


class IsIntegrationRunnableValidator(BaseValidator[ContentTypes]):
    error_code = "IN130"
    description = "validate that the integration is runable"
    rationale = (
        "Integrations must have a functional purpose, such as executing commands, fetching incidents, "
        "fetching indicators from a feed, or running a long-running process. "
    )
    error_message = "Could not find any runnable command in the integration.\nMust have at least one of: a command under the `commands` section, `isFetch: true`, `feed: true`, or `longRunning: true`."
    related_field = "commands, isfetch, feed, longRunning."
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.type),
                content_object=content_item,
            )
            for content_item in content_items
            if not any(
                [
                    content_item.commands,
                    content_item.is_feed,
                    content_item.is_fetch,
                    content_item.long_running,
                ]
            )
        ]
