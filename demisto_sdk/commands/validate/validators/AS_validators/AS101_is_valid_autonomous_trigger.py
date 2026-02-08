from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.trigger import Trigger
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Trigger]


class IsValidAutonomousTriggerValidator(BaseValidator[ContentTypes]):
    error_code = "AS101"
    description = (
        "Validate that triggers in autonomous packs have the correct autonomous fields."
    )
    rationale = (
        "Triggers in packs with pack_metadata managed: true and source: 'autonomous' "
        "must have grouping_element: 'Cortex Autonomous Rules' and is_auto_enabled: true."
    )
    error_message = (
        "The trigger is in an autonomous pack (managed: true, source: 'autonomous') "
        "but does not have the required autonomous fields. "
        "Current grouping_element: {0}, is_auto_enabled: {1}. "
        "Expected grouping_element: 'Cortex Autonomous Rules', is_auto_enabled: true."
    )
    fix_message = (
        "Set grouping_element to 'Cortex Autonomous Rules' and is_auto_enabled to true."
    )
    related_field = "grouping_element, is_auto_enabled"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    content_item.grouping_element or "N/A",
                    content_item.is_auto_enabled,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if is_invalid_autonomous_trigger(content_item)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Fix the trigger by setting grouping_element to 'Cortex Autonomous Rules' and is_auto_enabled to true.

        Args:
            content_item: The trigger content item to fix.

        Returns:
            FixResult with the fix message.
        """
        # Update the trigger's attributes (these will be saved via field_mapping)
        content_item.grouping_element = "Cortex Autonomous Rules"
        content_item.is_auto_enabled = True

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )


def is_invalid_autonomous_trigger(content_item: ContentTypes) -> bool:
    """
    Check if a trigger is in an autonomous pack but doesn't have the correct autonomous fields.

    Args:
        content_item: The trigger content item to validate.

    Returns:
        bool: True if the trigger is invalid (pack is autonomous but trigger doesn't have the right fields), False otherwise.
    """
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        # If there's no pack metadata, consider it valid (not autonomous)
        return False

    # Check if the pack is autonomous (both managed is true and source is "autonomous")
    is_managed = pack_metadata.get("managed", False)
    source = pack_metadata.get("source", "")

    is_autonomous_pack = is_managed is True and source == "autonomous"

    if not is_autonomous_pack:
        # If the pack is not autonomous, the trigger is valid (no validation needed)
        return False

    # If the pack IS autonomous, check if the trigger has the correct fields
    has_correct_grouping = content_item.grouping_element == "Cortex Autonomous Rules"
    has_auto_enabled = content_item.is_auto_enabled is True

    # The trigger is invalid if it doesn't have both required fields
    return not (has_correct_grouping and has_auto_enabled)
