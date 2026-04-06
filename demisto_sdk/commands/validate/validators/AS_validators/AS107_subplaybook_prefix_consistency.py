from __future__ import annotations

from typing import Iterable, List, Tuple

from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    FixResult,
    ValidationResult,
)

ContentTypes = Playbook

SUBPLAYBOOK_PREFIX = "subplaybook"


class SubplaybookPrefixConsistencyValidator(BaseValidator[ContentTypes]):
    error_code = "AS107"
    description = "Validate that subplaybook prefix is consistent across filename, id, and name fields."
    rationale = (
        "If a playbook has the 'subplaybook' prefix in any of its identifiers "
        "(filename, id, or name), all three must have this prefix for consistency."
    )
    error_message = (
        "The playbook has inconsistent 'subplaybook' prefix usage. "
        "Found prefix in: {0}. Missing prefix in: {1}. "
        "All of filename, id, and name must either have or not have the 'subplaybook' prefix."
    )
    fix_message = "Added 'subplaybook' prefix to {0}."
    related_field = "id, name"
    is_auto_fixable = True

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        results: List[ValidationResult] = []
        for content_item in content_items:
            has_prefix, missing_prefix = _check_subplaybook_prefix_consistency(
                content_item
            )
            if has_prefix and missing_prefix:
                results.append(
                    ValidationResult(
                        validator=self,
                        message=self.error_message.format(
                            ", ".join(has_prefix), ", ".join(missing_prefix)
                        ),
                        content_object=content_item,
                    )
                )
        return results

    def fix(self, content_item: ContentTypes) -> FixResult:
        """
        Fix the playbook by adding 'subplaybook' prefix to id and name if missing.

        Args:
            content_item: The playbook content item to fix.

        Returns:
            FixResult with the fix message.
        """
        fixed_fields = []

        # Check what needs to be fixed
        has_prefix, missing_prefix = _check_subplaybook_prefix_consistency(content_item)

        if not has_prefix:
            # No prefix anywhere, nothing to fix
            return FixResult(
                validator=self,
                message="No 'subplaybook' prefix found, no changes needed.",
                content_object=content_item,
            )

        # Add prefix to missing fields
        if "id" in missing_prefix:
            content_item.object_id = f"{SUBPLAYBOOK_PREFIX}-{content_item.object_id}"
            fixed_fields.append("id")

        if "name" in missing_prefix:
            content_item.name = f"{SUBPLAYBOOK_PREFIX}-{content_item.name}"
            fixed_fields.append("name")

        return FixResult(
            validator=self,
            message=self.fix_message.format(", ".join(fixed_fields)),
            content_object=content_item,
        )


def _check_subplaybook_prefix_consistency(
    content_item: ContentTypes,
) -> Tuple[List[str], List[str]]:
    """
    Check if a playbook has consistent 'subplaybook' prefix usage.

    Args:
        content_item: The playbook content item to validate.

    Returns:
        A tuple of two lists:
        - First list: locations where prefix is found
        - Second list: locations where prefix is missing
    """
    has_prefix = []
    missing_prefix = []

    # Check filename
    filename = content_item.path.stem  # Get filename without extension
    if filename.lower().startswith(SUBPLAYBOOK_PREFIX):
        has_prefix.append("filename")
    else:
        missing_prefix.append("filename")

    # Check id (object_id)
    if content_item.object_id and content_item.object_id.lower().startswith(
        SUBPLAYBOOK_PREFIX
    ):
        has_prefix.append("id")
    else:
        missing_prefix.append("id")

    # Check name
    if content_item.name and content_item.name.lower().startswith(SUBPLAYBOOK_PREFIX):
        has_prefix.append("name")
    else:
        missing_prefix.append("name")

    # If prefix is found in at least one location but not all, it's inconsistent
    if has_prefix and missing_prefix:
        return has_prefix, missing_prefix

    # Either all have prefix or none have prefix - consistent
    return [], []
