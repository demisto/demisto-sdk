from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Union[Playbook]


class PlaybookMustHaveAdoptedFieldValidator(BaseValidator[ContentTypes]):
    error_code = "AS104"
    description = "Validate that playbooks in autonomous packs have the 'adopted' field set to true."
    rationale = (
        "In autonomous packs (managed: true, source: 'autonomous'), all playbooks "
        "must have 'adopted: true' at the root level to indicate they have been "
        "adopted into the autonomous pack."
    )
    error_message = (
        "The playbook is in an autonomous pack (managed: true, source: 'autonomous') "
        "but is missing the required 'adopted: true' field."
    )
    fix_message = "Set 'adopted' to true on the playbook."
    related_field = "adopted"
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
            if _is_invalid_adopted_field(content_item)
        ]

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Fix the playbook by setting 'adopted' to True.

        Args:
            content_item: The playbook content item to fix.

        Returns:
            FixResult with the fix message.
        """
        content_item.adopted = True

        return FixResult(
            validator=self,
            message=self.fix_message,
            content_object=content_item,
        )


def _is_invalid_adopted_field(content_item: ContentTypes) -> bool:
    """
    Check if a playbook is in an autonomous pack but does not have 'adopted: true'.

    Args:
        content_item: The playbook content item to validate.

    Returns:
        bool: True if the playbook is invalid (autonomous pack but adopted is not True).
    """
    pack_metadata = content_item.in_pack.pack_metadata_dict  # type: ignore[union-attr]
    if not pack_metadata:
        return False

    is_managed = pack_metadata.get("managed", False)
    source = pack_metadata.get("source", "")
    is_autonomous_pack = is_managed is True and source == "autonomous"

    if not is_autonomous_pack:
        return False

    # Autonomous pack: adopted must be explicitly True
    return content_item.adopted is not True
