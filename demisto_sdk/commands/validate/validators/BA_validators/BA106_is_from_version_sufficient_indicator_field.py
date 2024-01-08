from __future__ import annotations

from typing import Iterable, List

from packaging.version import Version

from demisto_sdk.commands.content_graph.objects.indicator_field import IndicatorField
from demisto_sdk.commands.validate.validators.BA_validators.BA106_is_from_version_sufficient import (
    IsFromVersionSufficientValidator,
)
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

INDICATOR_FIELD_TYPE_TO_MIN_VERSION = {
    "html": "6.1.0",
    "grid": "5.5.0",
}
INDICATOR_FIELD_MIN_VERSION = "5.0.0"

ContentTypes = IndicatorField


class IsFromVersionSufficientIndicatorFieldValidator(
    IsFromVersionSufficientValidator, BaseValidator[ContentTypes]
):
    description = (
        "Validate that the indicator fromversion is sufficient according to its type"
    )
    error_message = "The fromversion of IndicatorField with type {0} must be at least {1}, current is {2}."

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.type,
                    expected_min_version,
                    content_item.fromversion,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (expected_min_version := is_from_version_insufficient(content_item))
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        version_to_set: str = INDICATOR_FIELD_TYPE_TO_MIN_VERSION.get(
            content_item.type, INDICATOR_FIELD_MIN_VERSION
        )
        content_item.fromversion = version_to_set
        return FixResult(
            validator=self,
            message=self.fix_message.format(version_to_set),
            content_object=content_item,
        )


def is_from_version_insufficient(content_item: ContentTypes) -> str:
    """Validate that the indicator type is sufficient according to its type.

    Args:
        content_item (ContentTypes): The indicator field to check wether its fromversion is sufficient.

    Returns:
        str: The expected min version if the version is insufficient. Otherwise, return an empty string.
    """
    expected_min_version = INDICATOR_FIELD_TYPE_TO_MIN_VERSION.get(
        content_item.type, INDICATOR_FIELD_MIN_VERSION
    )
    return (
        expected_min_version
        if Version(content_item.fromversion) < Version(expected_min_version)
        else ""
    )
