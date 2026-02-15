from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.list import List as ContentList
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, ContentList, Playbook]


class SourceInManagedPackValidator(BaseValidator[ContentTypes]):
    error_code = "MC101"
    description = (
        "Validate that content items in managed packs have the correct source field."
    )
    rationale = (
        "Content items in packs with pack_metadata managed: true "
        "must have a source field that matches the source in pack_metadata."
    )
    error_message = (
        "The content item is in a managed pack (managed: true) "
        "but {0}. "
        "Expected source: '{1}'."
    )
    fix_message = "Set source to '{0}' to match the pack metadata."
    related_field = "source"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results = []
        for content_item in content_items:
            error_reason, expected_source = get_source_validation_error(content_item)
            if error_reason:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            error_reason,
                            expected_source or "N/A",
                        ),
                        content_object=content_item,
                    )
                )
        return results

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Fix the content item by setting the source field to match pack metadata.

        Args:
            content_item: The content item to fix.

        Returns:
            FixResult with the fix message.
        """
        pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
        expected_source = pack_metadata.get("source", "")
        
        # Update the content item's source attribute
        content_item.source = expected_source

        return FixResult(
            validator=self,
            message=self.fix_message.format(expected_source),
            content_object=content_item,
        )


def get_source_validation_error(content_item: ContentTypes) -> tuple[str, str]:
    """
    Check if a content item in a managed pack has the correct source field.

    Args:
        content_item: The content item to validate.

    Returns:
        tuple: (error_reason, expected_source) where error_reason is empty string if valid,
               otherwise contains the reason for the error.
    """
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        # If there's no pack metadata, consider it valid (not managed)
        return "", ""

    # Check if the pack is managed
    is_managed = pack_metadata.get("managed", False)

    if not is_managed:
        # If the pack is not managed, the content item is valid (no validation needed)
        return "", ""

    # Get the expected source from pack metadata
    expected_source = pack_metadata.get("source", "")
    
    # Get the actual source from the content item
    actual_source = getattr(content_item, "source", "")

    # Check if source field is missing (empty string)
    if not actual_source:
        return "does not have a source field", expected_source

    # Check if source field matches pack metadata
    if actual_source != expected_source:
        return f"has source '{actual_source}' which does not match the pack metadata source", expected_source

    # The content item is valid
    return "", ""
