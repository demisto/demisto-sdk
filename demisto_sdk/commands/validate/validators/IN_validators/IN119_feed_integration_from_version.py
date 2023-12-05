from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Integration


class FeedIntegrationFromVersionValidator(BaseValidator[ContentTypes]):
    error_code = "IN119"
    description = (
        "Validate that a feed integration has a high enough fromversion field."
    )
    error_message = "The integration is a feed integration and therefore require a fromversion field of at least 5.5.0, current version is: {0}."
    fix_message = "Raised the fromversion field to 5.5.0"
    related_field = "fromversion"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(content_item.fromversion),
                content_object=content_item,
            )
            for content_item in content_items
            if content_item.is_feed
            and Version(content_item.fromversion) < Version("5.5.0")
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        content_item.fromversion = "5.5.0"
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )
