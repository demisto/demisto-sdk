from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.validate.validators.BA_validators.BA106_is_from_version_sufficient import (
    IsFromVersionSufficientValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    FixResult,
    ValidationResult,
)

ContentTypes = Integration
INTEGRATION_FROM_VERSION_DICT = {
    "powershell": "5.5.0",
    "feed": "5.5.0",
    "regular": "5.0.0",
}


class IsFromVersionSufficientIntegrationValidator(
    IsFromVersionSufficientValidator[ContentTypes]
):
    error_message = "The integration is a {0} integration and therefore require a fromversion field of at least {1}, current version is: {2}."

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
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
            if (integration_type := is_from_version_insufficient(content_item))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        integration_type = get_integration_type(content_item)
        content_item.fromversion = INTEGRATION_FROM_VERSION_DICT[integration_type]
        return FixResult(
            validator=self,
            message=self.fix_message.format(content_item.fromversion),
            content_object=content_item,
        )


def is_from_version_insufficient(content_item: ContentTypes) -> str:
    """Validate that the integration fromversion is sufficient according to it's type.

    Args:
        content_item (ContentTypes): the integration to check wether it's fromversion is sufficient.

    Returns:
        str: The integration type if the from version is insufficient, else an empty string.
    """
    integration_type = get_integration_type(content_item)
    return (
        integration_type
        if Version(content_item.fromversion)
        < Version(INTEGRATION_FROM_VERSION_DICT[integration_type])
        else ""
    )


def get_integration_type(content_item: ContentTypes) -> str:
    """Extract the integration type.

    Args:
        content_item (ContentTypes): the integration to extract its type.

    Returns:
        str: the integration type.
    """
    return (
        "powershell"
        if content_item.type == "powershell"
        else ("feed" if content_item.is_feed else "regular")
    )
