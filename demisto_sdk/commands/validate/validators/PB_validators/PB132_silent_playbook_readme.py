from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook]


class NoReadmeForSilentPlaybook(BaseValidator[ContentTypes]):
    error_code = "PB131"
    description = "A silent playbook is not allowed to have a README file."
    rationale = "To ensure that nothing about the playbook appears in the documentation.."
    error_message = (
        "A silent playbook is not allowed to have a README file.."
    )
    related_field = "isSilent"
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
            if content_item.is_silent
        ]


def is_valid_relationship(content_item: ContentTypes) -> bool:
    """
    Validates the relationship between a content item and its associated playbook/trigger.
    """
    if not content_item.is_silent:
        # If the content item is not marked as silent, it's automatically valid
        return True

    if content_item.content_type == ContentType.PLAYBOOK:
        return any(
            trigger.data.get("playbook_id") == content_item.data.get("id")
            and trigger.is_silent
            for trigger in content_item.pack.content_items.trigger
        )

    if content_item.content_type == ContentType.TRIGGER:
        return any(
            playbook.data.get("id") == content_item.data.get("playbook_id")
            and playbook.is_silent
            for playbook in content_item.pack.content_items.playbook
        )

    # Default case if content type is not PLAYBOOK or TRIGGER
    return True
