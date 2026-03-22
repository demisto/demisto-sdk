from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Playbook, Trigger]


class NoIsSilentInAutonomousPackValidator(BaseValidator[ContentTypes]):
    error_code = "AS105"
    description = "Validate that playbooks and triggers in autonomous packs do not have isSilent: true."
    rationale = (
        "In autonomous packs (managed: true, source: 'autonomous'), playbooks and triggers "
        "must not be marked as silent (isSilent: true), as silent items are incompatible "
        "with the autonomous execution model."
    )
    error_message = (
        "The {content_type} is in an autonomous pack (managed: true, source: 'autonomous') "
        "but is marked as isSilent: true. "
        "Autonomous pack items must not have isSilent set to true."
    )
    fix_message = "Removed isSilent: true from the item."
    related_field = "isSilent"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_type=content_item.content_type.value
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if is_invalid_silent_in_autonomous_pack(content_item)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Fix the item by removing the isSilent field.

        Args:
            content_item: The playbook or trigger content item to fix.

        Returns:
            FixResult with the fix message.
        """
        content_item.data.pop("isSilent", None)
        content_item.is_silent = False
        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )


def is_invalid_silent_in_autonomous_pack(content_item: ContentTypes) -> bool:
    """
    Check if a playbook or trigger is in an autonomous pack and is marked as isSilent: true.

    The check applies when the item is marked as silent AND the pack is autonomous
    (managed: true AND source: 'autonomous'). If the pack is autonomous, all items
    within it are considered autonomous as well.

    Args:
        content_item: The playbook or trigger content item to validate.

    Returns:
        bool: True if the item is invalid (autonomous pack + isSilent: true), False otherwise.
    """
    if not content_item.is_silent:
        return False

    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        return False

    is_managed = pack_metadata.get("managed", False)
    pack_source = pack_metadata.get("source", "")
    return is_managed is True and pack_source == "autonomous"
