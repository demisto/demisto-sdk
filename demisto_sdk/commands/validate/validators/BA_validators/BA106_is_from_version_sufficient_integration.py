from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)
from demisto_sdk.commands.validate.validators.super_classes.BA106_is_from_version_sufficient import (
    IsFromVersionSufficientValidator,
)

ContentTypes = Integration
INTEGRATION_FROM_VERSION_DICT = {
    "powershell": "5.5.0",
    "feed": "5.5.0",
    "regular": "5.0.0",
}


class IsFromVersionSufficientIntegrationValidator(
    IsFromVersionSufficientValidator, BaseValidator[ContentTypes]
):
    description = "Validate that an integration has a high enough fromversion field according to whether it's a powershell/feed/regular."
    error_message = "The integration is a {0} integration and therefore require a fromversion field of at least {1}, current version is: {2}."
    related_field = "fromversion"
    is_auto_fixable = True

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    integration_type,
                    INTEGRATION_FROM_VERSION_DICT[integration_type],
                    content_item.fromversion,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                integration_type := (
                    "powershell"
                    if content_item.type == "powershell"
                    else ("feed" if content_item.is_feed else "regular")
                )
            )
            and Version(content_item.fromversion)
            < Version(INTEGRATION_FROM_VERSION_DICT[integration_type])
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        integration_type = (
            "powershell"
            if content_item.type == "powershell"
            else ("feed" if content_item.is_feed else "regular")
        )
        content_item.fromversion = INTEGRATION_FROM_VERSION_DICT[integration_type]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.fromversion),
            content_object=content_item,
        )
