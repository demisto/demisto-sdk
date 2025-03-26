from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.content_item import ContentItem
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Playbook, Trigger]


class IsSilentPlaybookRelationshipsValidator(BaseValidator[ContentTypes]):
    error_code = "PB131"
    description = "Every silent trigger must correspond to a silent playbook in the same pack, and vice versa."
    rationale = "To ensure the effective operation of the silent playbook items."
    error_message = (
        "The {} is silent, but does not correspond to a silent {} in the pack."
    )
    related_field = "issilent"
    is_auto_fixable = False

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        def get_types_for_err_msg(c: ContentItem) -> tuple[ContentType, ContentType]:
            if isinstance(c, Trigger):
                return ContentType.TRIGGER, ContentType.PLAYBOOK
            return ContentType.PLAYBOOK, ContentType.TRIGGER

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(*get_types_for_err_msg(content_item)),
                content_object=content_item,
            )
            for content_item in content_items
            if not self.is_valid_relationship(content_item)
        ]

    def is_valid_relationship(self, content_item: ContentTypes) -> bool:
        """
        Validates the relationship between a content item and its associated playbook/trigger.
        """
        if not content_item.is_silent:
            # If the content item is not marked as silent, it's automatically valid
            return True

        if content_item.content_type == ContentType.PLAYBOOK:
            for trigger in self.graph.search(
                content_type=ContentType.TRIGGER, is_silent=True
            ):
                if trigger.data.get("playbook_id") == content_item.data.get("id"):
                    return True
            return False

        if content_item.content_type == ContentType.TRIGGER:
            for playbook in self.graph.search(
                content_type=ContentType.PLAYBOOK, is_silent=True
            ):
                if playbook.data.get("id") == content_item.data.get("playbook_id"):
                    return True
            return False

        # Default case if content type is not PLAYBOOK or TRIGGER
        return True
