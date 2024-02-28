from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import RelatedFileType
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
    description = "Check that the entity name or display name does not contain the entity type"
    error_message = "The following fields: {0} shouldn't contain the word '{1}'"
    related_field = "name, display"
    is_auto_fixable = False
    related_file_type = [RelatedFileType.YML]

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(
                    ", ".join(self.related_field), content_item.content_type
                ),
                content_object=content_item,
            )
            for content_item in content_items
            if is_name_or_display_name_contains_type(content_item)
        ]


def is_name_or_display_name_contains_type(content_item: ContentTypes):
    """
    Check if content item name or display name contains the content item type.
    Args:
        content_item (ContentTypes): The content item to check its name and display name fields.

    Returns:
        Boolean: True if one of the relevant felids contain the content item type, False otherwise.
    """
    content_type = content_item.content_type.lower()
    content_name = content_item.name.lower()

    if content_type == "integration":
        return content_type in (content_name, content_item.display_name.lower())
    else:
        return content_type in content_name
