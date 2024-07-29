from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.content_graph.common import ContentType
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

    def obtain_invalid_content_items(
        self, content_items: Iterable[ContentTypes]
    ) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    "fields" if len(invalid_fields) > 1 else "field",
                    ", ".join(invalid_fields),
                    content_item.content_type,
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_fields
                := validate_content_item_type_not_in_name_or_display_fields(
                    content_item
                )
            )
        ]


def validate_content_item_type_not_in_name_or_display_fields(
    content_item: ContentTypes,
) -> List[str]:
    """Checks if a content item has its type in its 'name' or 'display' fields and
    updates the 'incompatible_fields' with relevant fields for the validation's error message.

    Args:
        content_item (ContentTypes): The content item to validate.
        incompatible_fields (_type_): List of relevant content item fields to be printed in the validations error message.

    Returns:
        Names (e.g. `name`, `display_name`) of the invalid fields found.
    """
    invalid_fields = []
    fields = {"name": content_item.name}

    if content_item.content_type == ContentType.INTEGRATION:
        # only integrations have a display name
        fields["display"] = content_item.display_name

    for field_key, field_value in fields.items():
        if str(content_item.content_type.value).lower() in field_value.lower():
            invalid_fields.append(field_key)

    return invalid_fields
