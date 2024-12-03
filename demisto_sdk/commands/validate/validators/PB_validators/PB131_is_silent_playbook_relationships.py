
from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.validate.validators.base_validator import (
        BaseValidator,
        ValidationResult,
)

ContentTypes = Union[Playbook, Trigger]


class IsSilentPlaybookRelationshipsValidator(BaseValidator[ContentTypes]):
    error_code = "PB131"
    description = "A silent-Playbook/Trigger must point to a silent-Playbook/Trigger"
    rationale = "A silent-Playbook/Trigger must point to a silent-Playbook/Trigger"
    error_message = "Your silent-Playbook/Trigger does not point to a silent-Playbook/Trigger"
    related_field = ""
    is_auto_fixable = False

    
    def obtain_invalid_content_items(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message,
                content_object=content_item,
            )
            for content_item in content_items
            if not is_valid_relationship(content_item)
        ]

def is_valid_relationship(content_item: ContentTypes) -> bool:
    """
    Validates the relationship between a content item and its associated playbook/trigger.
    """
    if not content_item.data.get('isSilent', False):
        # If the content item is not marked as silent, it's automatically valid
        return True

    if content_item.content_type == ContentType.PLAYBOOK:
        return any(
            trigger.data.get('playbook_id') == content_item.data.get('id') and trigger.data.get('isSilent', False)
            for trigger in content_item.pack.content_items.trigger
        )

    if content_item.content_type == ContentType.TRIGGER:
        return any(
            playbook.data.get('id') == content_item.data.get('playbook_id') and playbook.data.get('isSilent', False)
            for playbook in content_item.pack.content_items.playbook
        )

    # Default case if content type is not PLAYBOOK or TRIGGER
    return True