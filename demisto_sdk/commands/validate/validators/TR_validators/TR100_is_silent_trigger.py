from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Trigger]


class IsSilentTriggerValidator(BaseValidator[ContentTypes]):
    error_code = "TR100"
    description = "Validate that the 'trigger_name', and file name of a silent trigger contain the 'silent-' prefix and include the field issilent: true."
    rationale = "A silent trigger must have the 'silent-' prefix in its trigger_name, and file name, and the field issilent: true."
    error_message = "Silent triggers must have 'silent-' as a prefix in the trigger_name and file name, and include the field issilent: true. One or more of these is missing."
    related_field = ""
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if is_invalid_silent(content_item)
        ]


def is_invalid_silent(content_item: ContentTypes) -> bool:
    return any(
        [
            content_item.is_silent,
            content_item.data.get("trigger_name", "").startswith("silent-"),
            content_item.path.name.startswith("silent-"),
        ]
    ) and not all(
        [
            content_item.is_silent,
            content_item.data.get("trigger_name", "").startswith("silent-"),
            content_item.path.name.startswith("silent-"),
        ]
    )
