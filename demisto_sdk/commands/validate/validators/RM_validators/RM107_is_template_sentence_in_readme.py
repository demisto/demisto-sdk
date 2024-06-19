from __future__ import annotations

from typing import Iterable, List, Union

from demisto_sdk.commands.common.constants import GitStatuses
from demisto_sdk.commands.content_graph.objects.integration import Integration
from demisto_sdk.commands.content_graph.objects.script import Script
from demisto_sdk.commands.content_graph.objects.playbook import Playbook
from demisto_sdk.commands.content_graph.objects.pack import Pack
from demisto_sdk.commands.validate.validators.base_validator import (
    BaseValidator,
    ValidationResult,
)

from demisto_sdk.commands.common.tools import search_substrings_by_line

ContentTypes = Union[Integration, Script, Playbook, Pack]


# error_code = "RP103"
# description = "Validate that the 'id' field of indicator type has valid value."
# error_message = ("The `id` field must consist of alphanumeric characters (A-Z, a-z, 0-9), whitespaces ( ), "
#                  "underscores (_), and ampersands (&) only.")
# rationale = "we want to make sure the id of the indicator type is valid."
# related_field = "id"
# is_auto_fixable = False

class IsTemplateNotInReadmeValidator(BaseValidator[ContentTypes]):
    error_code = "RM107"
    description = "Checks if there are the generic sentence '%%FILL HERE%%' in the README content."
    rationale = "Checks if there are the generic sentence '%%FILL HERE%%' in the README content."
    error_message = "The template '%%FILL HERE%%' does not exist in the README content."
    related_field = "readme.file_content"
    is_auto_fixable = False

    def is_valid(self, content_items: Iterable[ContentTypes]) -> List[ValidationResult]:
        """
        Checks if there are the generic sentence '%%FILL HERE%%' in the README content.

        Return:
            True if '%%FILL HERE%%' does not exist in the README content, and False if it does.
        """

        return [
            ValidationResult(
                validator=self,
                message=self.error_message.format(f"{invalid_lines}"),
                content_object=content_item,
            )
            for content_item in content_items
            if (
                invalid_lines := search_substrings_by_line(
                    phrases_to_search=["%%FILL HERE%%"],
                    text=content_item.readme.file_content
                )
            )
        ]
