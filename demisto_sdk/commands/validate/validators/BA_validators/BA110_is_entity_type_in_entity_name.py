from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

ContentTypes = Union[Integration, Script, Playbook]


class IsEntityTypeInEntityNameValidator(BaseValidator[ContentTypes]):
    error_code = "BA110"
    description = (
        "Check that the entity name or display name does not contain the entity type."
    )
    rationale = "Improves clarity and simplicity in the content repository"
    error_message = "The following {0}: {1} shouldn't contain the word '{2}'."
    related_field = "name, display"

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        incompatible_fields: list[str] = []
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "fields" if len(incompatible_fields) > 1 else "field",
                    ", ".join(incompatible_fields),
                    content_item.content_type,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if validate_content_item_type_not_in_name_or_display_fields(
                content_item, incompatible_fields
            )
        ]


def validate_content_item_type_not_in_name_or_display_fields(
    content_item: ContentTypes, incompatible_fields
) -> bool:
    """Checks if a content item has its type in its 'name' or 'display' fields and
    updates the 'incompatible_fields' with relevant fields for the validation's error message.

    Args:
        content_item (ContentTypes): The content item to validate.
        incompatible_fields (_type_): List of relevant content item fields to be printed in the validations error message.

    Returns:
        bool: True if the content item's 'name' or 'display' fields contain the content item type, False otherwise.
    """
    content_type = content_item.content_type.lower()
    if str(content_item.content_type) == "ContentType.INTEGRATION":
        incompatible_fields += ["name"] * (
            content_type in content_item.name.lower()
        ) + ["display"] * (content_type in content_item.display_name.lower())
    else:
        incompatible_fields += ["name"] * (content_type in content_item.name.lower())
    return bool(incompatible_fields)
