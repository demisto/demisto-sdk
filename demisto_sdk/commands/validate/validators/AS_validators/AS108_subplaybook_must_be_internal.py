from __future__ import annotations

from typing import Iterable, List

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook

SUBPLAYBOOK_PREFIX = "subplaybook"


class SubplaybookMustBeInternalValidator(BaseValidator[ContentTypes]):
    error_code = "AS108"
    description = "Validate that subplaybooks in autonomous packs have the 'internal' field set to true."
    rationale = (
        "In autonomous packs (managed: true, source: 'autonomous'), playbooks with the 'subplaybook' "
        "prefix in their filename, id, or name are intended to be used as sub-playbooks and must have "
        "'internal: true' to prevent them from being directly accessible."
    )
    error_message = (
        "The playbook is in an autonomous pack (managed: true, source: 'autonomous') and has the 'subplaybook' "
        "prefix but does not have 'internal: true'. Subplaybooks must be marked as internal."
    )
    fix_message = "Set 'internal' to true on the subplaybook."
    related_field = "internal"
    is_auto_fixable = True

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
            if _is_subplaybook_without_internal(content_item)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Fix the playbook by setting 'internal' to True.

        Args:
            content_item: The playbook content item to fix.

        Returns:
            FixResult with the fix message.
        """
        content_item.internal = True

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )


def _is_subplaybook_without_internal(content_item: ContentTypes) -> bool:
    """
    Check if a playbook in an autonomous pack is a subplaybook (has 'subplaybook' prefix)
    but does not have 'internal: true'.

    Args:
        content_item: The playbook content item to validate.

    Returns:
        bool: True if the playbook is in an autonomous pack, is a subplaybook, and does not have internal=True.
    """
    # Check if this is an autonomous pack
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    is_managed = pack_metadata.get("managed", False)
    source = pack_metadata.get("source", "")
    is_autonomous_pack = is_managed is True and source == "autonomous"

    if not is_autonomous_pack:
        return False

    # Check if any of filename, id, or name has the subplaybook prefix
    filename = content_item.path.stem  # Get filename without extension
    has_subplaybook_prefix: bool = (
        filename.lower().startswith(SUBPLAYBOOK_PREFIX)
        or (
            bool(content_item.object_id)
            and content_item.object_id.lower().startswith(SUBPLAYBOOK_PREFIX)
        )
        or (
            bool(content_item.name)
            and content_item.name.lower().startswith(SUBPLAYBOOK_PREFIX)
        )
    )

    # If it's a subplaybook but internal is not True, it's invalid
    return bool(has_subplaybook_prefix and content_item.internal is not True)
